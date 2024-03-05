def TV(P1, P2):
    keys = set(P1.keys()).union(P2.keys())
    s = 0
    for k in keys :
        if k not in P1.keys():
            s += P2[k]
        elif k not in P2.keys():
            s += P1[k]
        else :
            s += abs(P1[k] - P2[k])
    return s / 2