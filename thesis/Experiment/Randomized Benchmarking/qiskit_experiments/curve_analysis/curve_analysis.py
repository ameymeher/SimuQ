# This code is part of Qiskit.
#
# (C) Copyright IBM 2021.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""
Analysis class for curve fitting.
"""
# pylint: disable=invalid-name

from typing import Dict, List, Tuple, Union, Optional
from functools import partial
from itertools import groupby
from operator import itemgetter

import lmfit
import numpy as np
import pandas as pd
from uncertainties import unumpy as unp

from qiskit_experiments.framework import ExperimentData, AnalysisResultData
from qiskit_experiments.data_processing.exceptions import DataProcessorError

from .base_curve_analysis import BaseCurveAnalysis, PARAMS_ENTRY_PREFIX
from .curve_data import FitOptions, CurveFitResult
from .scatter_table import ScatterTable
from .utils import (
    eval_with_uncertainties,
    convert_lmfit_result,
    shot_weighted_average,
    inverse_weighted_variance,
    sample_average,
)


class CurveAnalysis(BaseCurveAnalysis):
    """Base class for curve analysis with single curve group.

    The fit parameters from the series defined under the analysis class are all shared
    and the analysis performs a single multi-objective function optimization.

    A subclass may override these methods to customize the fit workflow.

    .. rubric:: _run_data_processing

    This method performs data processing and returns the processed dataset.
    By default, it internally calls the :class:`.DataProcessor` instance from
    the `data_processor` analysis option and processes the experiment data payload
    to create Y data with uncertainty.
    X data and other metadata are generated within this method by inspecting the
    circuit metadata. The series classification is also performed based upon the
    matching of circuit metadata and :attr:`SeriesDef.filter_kwargs`.

    .. rubric:: _format_data

    This method consumes the processed dataset and outputs the formatted dataset.
    By default, this method takes the average of y values over
    the same x values and then sort the entire data by x values.

    .. rubric:: _generate_fit_guesses

    This method creates initial guesses for the fit parameters.
    See :ref:`curve_analysis_init_guess` for details.

    .. rubric:: _run_curve_fit

    This method performs the fitting with predefined fit models and the formatted dataset.
    This method internally calls the :meth:`_generate_fit_guesses` method.
    Note that this is a core functionality of the :meth:`_run_analysis` method,
    that creates fit result objects from the formatted dataset.

    .. rubric:: _evaluate_quality

    This method evaluates the quality of the fit based on the fit result.
    This returns "good" when reduced chi-squared is less than 3.0.
    Usually it returns string "good" or "bad" according to the evaluation.

    .. rubric:: _create_analysis_results

    This method creates analysis results for important fit parameters
    that might be defined by analysis options ``result_parameters``.

    .. rubric:: _create_curve_data

    This method creates analysis results containing the formatted dataset,
    i.e. data used for the fitting.
    Entries are created when the analysis option ``return_data_points`` is ``True``.
    If analysis consists of multiple series, an analysis result is created for
    each series definition.

    .. rubric:: _create_figures

    This method creates figures by consuming the scatter table data.
    Figures are created when the analysis option ``plot`` is ``True``.

    .. rubric:: _initialize

    This method initializes analysis options against input experiment data.
    Usually this method is called before other methods are called.

    """

    def __init__(
        self,
        models: Optional[List[lmfit.Model]] = None,
        name: Optional[str] = None,
    ):
        """Initialize data fields that are privately accessed by methods.

        Args:
            models: List of LMFIT ``Model`` class to define fitting functions and
                parameters. If multiple models are provided, the analysis performs
                multi-objective optimization where the parameters with the same name
                are shared among provided models. When multiple models are provided,
                user must specify the ``data_subfit_map`` value in the analysis options
                to allocate experimental results to a particular fit model.
            name: Optional. Name of this analysis.
        """
        super().__init__()

        self._models = models or []
        self._name = name or self.__class__.__name__

    @property
    def name(self) -> str:
        """Return name of this analysis."""
        return self._name

    @property
    def parameters(self) -> List[str]:
        """Return parameters of this curve analysis."""
        unite_params = []
        for model in self._models:
            for name in model.param_names:
                if name not in unite_params and name not in self.options.fixed_parameters:
                    unite_params.append(name)
        return unite_params

    @property
    def models(self) -> List[lmfit.Model]:
        """Return fit models."""
        return self._models

    def model_names(self) -> List[str]:
        """Return model names."""
        return [getattr(m, "_name", f"model-{i}") for i, m in enumerate(self._models)]

    def _run_data_processing(
        self,
        raw_data: List[Dict],
        category: str = "raw",
    ) -> ScatterTable:
        """Perform data processing from the experiment result payload.

        Args:
            raw_data: Payload in the experiment data.
            category: Category string of the output dataset.

        Returns:
            Processed data that will be sent to the formatter method.

        Raises:
            DataProcessorError: When key for x values is not found in the metadata.
            ValueError: When data processor is not provided.
        """
        opt = self.options

        # Create table
        if opt.filter_data:
            to_process = [d for d in raw_data if opt.filter_data.items() <= d["metadata"].items()]
        else:
            to_process = raw_data

        # This must align with ScatterTable columns. Use struct array.
        dtypes = np.dtype(
            [
                ("xval", float),
                ("yval", float),
                ("yerr", float),
                ("name", "U30"),
                ("class_id", int),
                ("category", "U30"),
                ("shots", int),
            ]
        )

        # Prepare circuit metadata to data class mapper from data_subfit_map value.
        if len(self._models) == 1:
            classifier = {self.model_names()[0]: {}}
        else:
            classifier = self.options.data_subfit_map

        source = np.empty(len(to_process), dtype=dtypes)
        for idx, datum in enumerate(to_process):
            metadata = datum["metadata"]
            try:
                xval = metadata[opt.x_key]
            except KeyError as ex:
                raise DataProcessorError(
                    f"X value key {opt.x_key} is not defined in the circuit metadata."
                ) from ex
            source[idx]["xval"] = xval
            source[idx]["shots"] = datum.get("shots", -1)

            # Assign entry name and class id
            for class_id, (name, spec) in enumerate(classifier.items()):
                if spec.items() <= metadata.items():
                    source[idx]["class_id"] = class_id
                    source[idx]["name"] = name
                    break
            else:
                # This is unclassified data.
                # Assume that normal ID will never become negative number.
                # This is numpy struct array object and cannot store pandas nullable integer.
                source[idx]["class_id"] = -1
                source[idx]["name"] = ""

        # Compute y value
        if not self.options.data_processor:
            raise ValueError(
                f"Data processor is not set for the {self.__class__.__name__} instance. "
                "Initialize the instance with the experiment data, or set the "
                "data_processor analysis options."
            )
        processed_values = self.options.data_processor(to_process)
        source["yval"] = unp.nominal_values(processed_values).flatten()
        source["yerr"] = unp.std_devs(processed_values).flatten()
        source["category"] = category

        table = ScatterTable(data=source)

        # Replace temporary -1 value with nullable integer
        table["class_id"] = table["class_id"].replace(-1, pd.NA)
        table["shots"] = table["shots"].replace(-1, pd.NA)

        return table

    def _format_data(
        self,
        curve_data: ScatterTable,
        category: str = "formatted",
    ) -> ScatterTable:
        """Postprocessing for preparing the fitting data.

        Args:
            curve_data: Processed dataset created from experiment results.
            category: Category string of the output dataset.

        Returns:
            New scatter table instance including data to fit.
        """
        averaging_methods = {
            "shots_weighted": shot_weighted_average,
            "iwv": inverse_weighted_variance,
            "sample": sample_average,
        }

        columns = list(curve_data.columns)
        sort_by = itemgetter(
            columns.index("class_id"),
            columns.index("xval"),
        )
        # Use python native groupby method on ndarray. This is more performant than pandas one.
        average = averaging_methods[self.options.average_method]
        model_names = self.model_names()
        formatted = []
        for (_, xv), g in groupby(sorted(curve_data.values, key=sort_by), key=sort_by):
            g_values = np.array(list(g))
            g_dict = dict(zip(columns, g_values.T))
            avg_yval, avg_yerr, shots = average(g_dict["yval"], g_dict["yerr"], g_dict["shots"])
            data_name = g_dict["name"][0]
            try:
                # Map data index to model index through assigned name.
                # Data name should match with the model name.
                # Otherwise, the model index is unclassified.
                model_id = model_names.index(data_name)
            except ValueError:
                model_id = pd.NA
            averaged = dict.fromkeys(columns)
            averaged["category"] = category
            averaged["xval"] = xv
            averaged["yval"] = avg_yval
            averaged["yerr"] = avg_yerr
            averaged["name"] = data_name
            averaged["class_id"] = model_id
            averaged["shots"] = shots
            formatted.append(list(averaged.values()))

        return curve_data.append_list_values(formatted)

    def _generate_fit_guesses(
        self,
        user_opt: FitOptions,
        curve_data: ScatterTable,  # pylint: disable=unused-argument
    ) -> Union[FitOptions, List[FitOptions]]:
        """Create algorithmic initial fit guess from analysis options and curve data.

        Args:
            user_opt: Fit options filled with user provided guess and bounds.
            curve_data: Formatted data collection to fit.

        Returns:
            List of fit options that are passed to the fitter function.
        """
        return user_opt

    def _run_curve_fit(
        self,
        curve_data: ScatterTable,
    ) -> CurveFitResult:
        """Perform curve fitting on given data collection and fit models.

        Args:
            curve_data: Formatted data to fit.

        Returns:
            The best fitting outcome with minimum reduced chi-squared value.
        """
        unite_parameter_names = []
        for model in self._models:
            # Seems like this is not efficient looping, but using set operation sometimes
            # yields bad fit. Not sure if this is an edge case, but
            # `TestRamseyXY` unittest failed due to the significant chisq value
            # in which the least_square fitter terminates with `xtol` rather than `ftol`
            # condition, i.e. `ftol` condition indicates termination by cost function.
            # This code respects the ordering of parameters so that it matches with
            # the signature of fit function and it is backward compatible.
            # In principle this should not matter since LMFIT maps them with names
            # rather than index. Need more careful investigation.
            for name in model.param_names:
                if name not in unite_parameter_names:
                    unite_parameter_names.append(name)

        default_fit_opt = FitOptions(
            parameters=unite_parameter_names,
            default_p0=self.options.p0,
            default_bounds=self.options.bounds,
            **self.options.lmfit_options,
        )

        # Bind fixed parameters if not empty
        if self.options.fixed_parameters:
            fixed_parameters = {
                k: v for k, v in self.options.fixed_parameters.items() if k in unite_parameter_names
            }
            default_fit_opt.p0.set_if_empty(**fixed_parameters)
        else:
            fixed_parameters = {}

        fit_options = self._generate_fit_guesses(default_fit_opt, curve_data)

        if isinstance(fit_options, FitOptions):
            fit_options = [fit_options]

        # Create convenient function to compute residual of the models.
        partial_residuals = []
        valid_uncertainty = np.all(np.isfinite(curve_data.yerr.to_numpy()))
        for i, sub_data in list(curve_data.groupby("class_id")):
            if valid_uncertainty:
                nonzero_yerr = np.where(
                    np.isclose(sub_data.yerr, 0.0),
                    np.finfo(float).eps,
                    sub_data.yerr,
                )
                raw_weights = 1 / nonzero_yerr
                # Remove outlier. When all sample values are the same with sample average,
                # or sampling error is zero with shot-weighted average,
                # some yerr values might be very close to zero, yielding significant weights.
                # With such outlier, the fit doesn't sense residual of other data points.
                maximum_weight = np.percentile(raw_weights, 90)
                weights = np.clip(raw_weights, 0.0, maximum_weight)
            else:
                weights = None
            model_residual = partial(
                self._models[i]._residual,
                data=sub_data.yval.to_numpy(),
                weights=weights,
                x=sub_data.xval.to_numpy(),
            )
            partial_residuals.append(model_residual)

        # Run fit for each configuration
        res = None
        for fit_option in fit_options:
            # Setup parameter configuration, i.e. init value, bounds
            guess_params = lmfit.Parameters()
            for name in unite_parameter_names:
                bounds = fit_option.bounds[name] or (-np.inf, np.inf)
                guess_params.add(
                    name=name,
                    value=fit_option.p0[name],
                    min=bounds[0],
                    max=bounds[1],
                    vary=name not in fixed_parameters,
                )

            try:
                with np.errstate(all="ignore"):
                    new = lmfit.minimize(
                        fcn=lambda x: np.concatenate([p(x) for p in partial_residuals]),
                        params=guess_params,
                        method=self.options.fit_method,
                        scale_covar=not valid_uncertainty,
                        nan_policy="omit",
                        **fit_option.fitter_opts,
                    )
            except Exception:  # pylint: disable=broad-except
                continue

            if res is None or not res.success:
                res = new
                continue

            if new.success and res.redchi > new.redchi:
                res = new

        return convert_lmfit_result(
            res,
            self._models,
            curve_data.xval.to_numpy(),
            curve_data.yval.to_numpy(),
        )

    def _create_figures(
        self,
        curve_data: ScatterTable,
    ) -> List["matplotlib.figure.Figure"]:
        """Create a list of figures from the curve data.

        Args:
            curve_data: Scatter data table containing all data points.

        Returns:
            A list of figures.
        """
        for name, data in list(curve_data.groupby("name")):
            # Plot raw data scatters
            if self.options.plot_raw_data:
                raw_data = data[data.category == "raw"]
                self.plotter.set_series_data(
                    series_name=name,
                    x=raw_data.xval.to_numpy(),
                    y=raw_data.yval.to_numpy(),
                )
            # Plot formatted data scatters
            formatted_data = data[data.category == self.options.fit_category]
            self.plotter.set_series_data(
                series_name=name,
                x_formatted=formatted_data.xval.to_numpy(),
                y_formatted=formatted_data.yval.to_numpy(),
                y_formatted_err=formatted_data.yerr.to_numpy(),
            )
            # Plot fit lines
            line_data = data[data.category == "fitted"]
            if len(line_data) == 0:
                continue
            self.plotter.set_series_data(
                series_name=name,
                x_interp=line_data.xval.to_numpy(),
                y_interp=line_data.yval.to_numpy(),
            )
            fit_stdev = line_data.yerr.to_numpy()
            if np.isfinite(fit_stdev).all():
                self.plotter.set_series_data(
                    series_name=name,
                    y_interp_err=fit_stdev,
                )

        return [self.plotter.figure()]

    def _run_analysis(
        self,
        experiment_data: ExperimentData,
    ) -> Tuple[List[AnalysisResultData], List["pyplot.Figure"]]:
        analysis_results = []
        figures = []

        # Flag for plotting can be "always", "never", or "selective"
        # the analysis option overrides self._generate_figures if set
        if self.options.get("plot", None):
            plot = "always"
        elif self.options.get("plot", None) is False:
            plot = "never"
        else:
            plot = getattr(self, "_generate_figures", "always")

        # Prepare for fitting
        self._initialize(experiment_data)

        table = self._format_data(self._run_data_processing(experiment_data.data()))
        formatted_subset = table[table.category == self.options.fit_category]
        fit_data = self._run_curve_fit(formatted_subset)

        if fit_data.success:
            quality = self._evaluate_quality(fit_data)
        else:
            quality = "bad"

        # After the quality is determined, plot can become a boolean flag for whether
        # to generate the figure
        plot_bool = plot == "always" or (plot == "selective" and quality == "bad")

        if self.options.return_fit_parameters:
            # Store fit status overview entry regardless of success.
            # This is sometime useful when debugging the fitting code.
            overview = AnalysisResultData(
                name=PARAMS_ENTRY_PREFIX + self.name,
                value=fit_data,
                quality=quality,
                extra=self.options.extra,
            )
            analysis_results.append(overview)

        if fit_data.success:
            # Add fit data to curve data table
            fit_curves = []
            columns = list(table.columns)
            model_names = self.model_names()
            for i, sub_data in list(formatted_subset.groupby("class_id")):
                xval = sub_data.xval.to_numpy()
                if len(xval) == 0:
                    # If data is empty, skip drawing this model.
                    # This is the case when fit model exist but no data to fit is provided.
                    continue
                # Compute X, Y values with fit parameters.
                xval_fit = np.linspace(np.min(xval), np.max(xval), num=100, dtype=float)
                yval_fit = eval_with_uncertainties(
                    x=xval_fit,
                    model=self._models[i],
                    params=fit_data.ufloat_params,
                )
                model_fit = np.full((100, len(columns)), None, dtype=object)
                fit_curves.append(model_fit)
                model_fit[:, columns.index("xval")] = xval_fit
                model_fit[:, columns.index("yval")] = unp.nominal_values(yval_fit)
                if fit_data.covar is not None:
                    model_fit[:, columns.index("yerr")] = unp.std_devs(yval_fit)
                model_fit[:, columns.index("name")] = model_names[i]
                model_fit[:, columns.index("class_id")] = i
                model_fit[:, columns.index("category")] = "fitted"
            table = table.append_list_values(other=np.vstack(fit_curves))
            analysis_results.extend(
                self._create_analysis_results(
                    fit_data=fit_data,
                    quality=quality,
                    **self.options.extra.copy(),
                )
            )

        if self.options.return_data_points:
            # Add raw data points
            analysis_results.extend(self._create_curve_data(curve_data=formatted_subset))

        if plot_bool:
            if fit_data.success:
                self.plotter.set_supplementary_data(
                    fit_red_chi=fit_data.reduced_chisq,
                    primary_results=[r for r in analysis_results if not r.name.startswith("@")],
                )
            figures.extend(self._create_figures(curve_data=table))

        return analysis_results, figures

    def __getstate__(self):
        state = self.__dict__.copy()
        # Convert models into JSON str.
        # This object includes local function and cannot be pickled.
        source = [m.dumps() for m in state["_models"]]
        state["_models"] = source
        return state

    def __setstate__(self, state):
        model_objs = []
        for source in state.pop("_models"):
            tmp_mod = lmfit.Model(func=None)
            mod = tmp_mod.loads(s=source)
            model_objs.append(mod)
        self.__dict__.update(state)
        self._models = model_objs
