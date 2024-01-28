import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Read the data from the Excel file
data = pd.read_excel('Optimization Level experiments.xlsx')

# Separate the data for use_pulse=True and use_pulse=False
true_data = data[data['use_pulse'] == True]
false_data = data[data['use_pulse'] == False]

# Create separate line plots for use_pulse=True and use_pulse=False
plt.figure(figsize=(12, 6))

# Define a custom color palette for more contrasting colors
custom_palette = sns.color_palette("husl", n_colors=len(data['optimization_level'].unique()))

# Plot for use_pulse=True
plt.subplot(1, 2, 1)  # Create the first subplot
sns.lineplot(data=true_data[true_data['N'] == 4], x='T', y='tv_value', hue='optimization_level', palette=custom_palette, marker='o', err_style=None)
plt.title('use_pulse=True')
plt.xlabel('T')
plt.ylabel('tv_value')

# Set the y-axis scale for the first subplot
y_min = 0
y_max = 1
plt.ylim(y_min, y_max)

# Plot for use_pulse=False
plt.subplot(1, 2, 2)  # Create the second subplot
sns.lineplot(data=false_data[false_data['N'] == 4], x='T', y='tv_value', hue='optimization_level', palette=custom_palette, marker='o', err_style=None)
plt.title('use_pulse=False')
plt.xlabel('T')
plt.ylabel('tv_value')

# Set the y-axis scale for the second subplot
y_min = 0
y_max = 1
plt.ylim(y_min, y_max)

# Set a common title for both subplots
plt.suptitle('N=4')

plt.tight_layout()  # Ensure plots do not overlap

# Show the plots
plt.show()
