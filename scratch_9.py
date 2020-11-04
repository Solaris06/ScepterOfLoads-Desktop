lines = open(r'C:\Users\yourt\PycharmProjects\LoadScepter\nick_shadow.csv').readlines()[2::2]
lines = list(dict.fromkeys(lines))
lines.sort(key=lambda l: float(l.split(",")[0]))
nogaps = [lines[0]]
gstart, gdur, gend = list(map(float, lines[0].split(",")))
for gapl in lines:
    ngstart, ngdur, ngend = list(map(float, gapl.split(",")))
    if abs(gend - ngstart) <= 0.08:
        gdur += ngdur
        gend = ngend
    else:

        nogaps.append("{},{},{}\n".format(gstart,gdur,gend))
        gstart = ngstart
        gend = ngend
        gdur = ngdur


open('flub_55clean.csv', 'w').write("".join(nogaps[2:]))
