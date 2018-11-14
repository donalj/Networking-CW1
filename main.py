import glob
import json
import os
import time
from pprint import pprint
from urllib2 import urlopen

from BeautifulSoup import BeautifulSoup
from gmplot import gmplot


def parseFiles(input, target):
    files = glob.glob(input)

    t = target
    count = 0
    # print input, target
    for file in files:
        file_name = file.replace(input.replace("*.txt", ""), "")
        file_name = file_name.replace("./trtemp/", "")
        file_name = file_name.replace("www.", "")
        file_name = file_name.replace(".ac.uk.txt", "")
        file_name = t + file_name
        # print file_name
        output = []
        exists = os.path.isfile(file_name)

        if exists:
            print "file " + file_name + " already exists"
        else:
            with open(file) as f:
                line = f.readline()
                line = line.replace("*", "")
                while line:
                    dict = {'Hostname': 'name', 'IP': 'ip', 'City': 'city', 'ISP': 'isp', 'Org': 'org',
                            'latitude': 'lat', 'longitude': 'long'}
                    name, ip = line.split(',')
                    ip = ip.rstrip()

                    if name == '*':
                        line = f.readline()

                    else:
                        baseurl = "http://ip-api.com/json/" + ip
                        if count == 140:
                            print "Sleeping for 60 seconds to avoid ban"
                            time.sleep(61)
                            count = 0
                            print "Finished sleeping"

                        j = urlopen(baseurl)
                        json_string = j.read()
                        parsed_json = json.loads(json_string)
                        count += 1
                        if parsed_json['status'] == 'fail':
                            print "this one failed " + name + " " + ip
                            dict['Hostname'] = name
                            dict['IP'] = ip
                            dict['latitude'] = 'unknown'
                            dict['longitude'] = 'unknown'
                            dict['ISP'] = 'unknown'
                            dict['City'] = 'unknown'
                            dict['Org'] = 'unknown'

                        else:
                            dict['Hostname'] = name
                            dict['IP'] = ip
                            dict['latitude'] = parsed_json['lat']
                            dict['longitude'] = parsed_json['lon']
                            dict['ISP'] = parsed_json['isp']
                            dict['City'] = parsed_json['city']
                            dict['Org'] = parsed_json['org']

                        output.append(dict)
                        line = f.readline()

            f.close
            with open(file_name, 'w') as fout:
                json.dump(output, fout)
                print "Outputting file: " + file_name


def stripHost(hop, country):
    name = hop['Hostname']
    org = hop['Org']
    if country == "canada":
        if "Canarie" in org or "canarie" in name:
            location = name
        else:
            location = "noncanarie: " + name

        return location
    else:
        if "ja.net" in name:
            if len(name.split('.')) == 4:
                prefix, location, ja, net = name.split('.')
            elif len(name.split('.')) == 5:
                prefix, location, idk, ja, net = name.split('.')
            else:
                location, ja, net = name.split('.')
        else:
            location = "nonjanet: " + name

        return location


def getServers(loc, country):
    servers = []
    files = glob.glob(loc + "/*")
    for f in files:
        check = True
        with open(f) as data_file:
            data = json.load(data_file)
            for index, hop in enumerate(data):
                name = hop['Hostname']
                for d in servers:
                    if d['Hostname'] == name:
                        check = False
                if check:
                    hop['Hostname'] = stripHost(hop, country)
                    hop = fixJanet(hop)
                    servers.append(hop)
    return servers


def getLabels(servers, g):
    labels = []
    for idx, server in enumerate(servers):
        n = server.name
        d = {'name': n}
        labels.append(d)
        g.nodes[idx]['name'] = n
    return g


def buildMap(gmap, servers, colour):
    lats = []
    longs = []
    names = []
    for server in servers:
        lats.append(server['latitude'])
        longs.append(server['longitude'])
        names.append(server['Hostname'])

    for i, lat in enumerate(lats):
        # print lats[i], longs[i], names[i]
        gmap.marker(lats[i], longs[i], title=names[i], c=colour)

    return gmap


def singleRoute(gmap, uni, country):
    source = uni
    lats = []
    longs = []
    names = []
    with open(source) as data_file:
        data = json.load(data_file)
        for index, hop in enumerate(data):
            hop['Hostname'] = stripHost(hop, country)
            hop = fixJanet(hop)
            lats.append(hop['latitude'])
            longs.append(hop['longitude'])
            names.append(hop['Hostname'])
            gmap.marker(hop['latitude'], hop['longitude'], title=hop['Hostname'], c="red")
        gmap.plot(lats, longs, "blue", edge_width=5)
    return gmap


def buildHeatMap(gmap, servers):
    lats = []
    longs = []
    names = []
    for server in servers:
        lats.append(server['latitude'])
        longs.append(server['longitude'])
        names.append(server['Hostname'])

    gmap.heatmap(lats, longs, dissipating=True, radius=30)
    return gmap


def scrapeLinks(input):
    shit = ""
    html_page = urlopen(input)
    soup = BeautifulSoup(html_page)
    for link in soup.findAll('a'):
        web = link.get('href')
        if not "univcan" in web:
            shit = shit + web + "\n"

    canadian = open("canadian.txt", "w")
    canadian.write(shit)
    canadian.close()


def buildCompound(gmap, country):
    ukfiles = glob.glob("./newjsonroutes/*")
    cfiles = glob.glob("./Canada/json/*")
    if country == "uk":
        for file in ukfiles:
            gmap = singleRoute(gmap, file, "uk")
        return gmap
    else:
        for file in cfiles:
            gmap = singleRoute(gmap, file, "canada")
        return gmap


def mapStuff(baseuk, basecanada):
    canadaservers = [dict(tupleized) for tupleized in set(tuple(item.items()) for item in basecanada)]
    canadaservers = sorted(canadaservers, key=lambda k: k['Hostname'])
    ukservers = [dict(tupleized) for tupleized in set(tuple(item.items()) for item in baseuk)]
    ukservers = sorted(ukservers, key=lambda k: k['Hostname'])
    janet = filter(lambda server: not "nonjanet" in server['Hostname'], ukservers)
    canarie = filter(lambda server: not "noncanarie" in server['Hostname'], canadaservers)
    nonjanet = filter(lambda server: "nonjanet" in server['Hostname'], ukservers)
    noncanarie = filter(lambda server: "noncanarie" in server['Hostname'], canadaservers)

    for server in canadaservers:
        print server['Hostname']
    # pprint(canadaservers)
    # gmap = gmplot.GoogleMapPlotter(0, 0, 3, 'AIzaSyAtbi8u-E8RbY_Y0qeyUz4vdPJPGcLwY6c')
    #
    # gmap = buildMap(gmap, nonjanet, "blue")
    # gmap.draw("nonjanet.html")


    # gmap = gmplot.GoogleMapPlotter(0, 0, 3, 'AIzaSyAtbi8u-E8RbY_Y0qeyUz4vdPJPGcLwY6c')
    # gmap = buildMap(gmap, janet, "green")
    # gmap.draw("janet.html")

    gmap = gmplot.GoogleMapPlotter(0, 0, 3, 'AIzaSyAtbi8u-E8RbY_Y0qeyUz4vdPJPGcLwY6c')
    # gmap = buildMap(gmap, canarie, "white")
    # gmap = buildMap(gmap, noncanarie, "red")
    # gmap.draw("canada.html")

    # heat = gmplot.GoogleMapPlotter(0, 0, 3, 'AIzaSyAtbi8u-E8RbY_Y0qeyUz4vdPJPGcLwY6c')
    # heat = buildHeatMap(heat, ukservers)
    # heat.draw("heatmap_uk.html")

    # heat = gmplot.GoogleMapPlotter(0, 0, 3, 'AIzaSyAtbi8u-E8RbY_Y0qeyUz4vdPJPGcLwY6c')
    # heat = buildHeatMap(heat, canadaservers)
    # heat.draw("heatmap_ca.html")

    # Canada
    # cfiles = glob.glob("./Canada/json/*")
    #
    # for file in cfiles:
    #     gmap = gmplot.GoogleMapPlotter(0, 0, 3, 'AIzaSyAtbi8u-E8RbY_Y0qeyUz4vdPJPGcLwY6c')
    #     gmap = singleRoute(gmap, file, "canada")
    #     try:
    #         gmap.draw("./Canada/maps/" + file.replace("./Canada/json/", "") + ".html")
    #     except TypeError:
    #         print file
    #
    # UK
    ukfiles = glob.glob("./newjsonroutes/*")

    for file in ukfiles:
        gmap = gmplot.GoogleMapPlotter(0, 0, 3, 'AIzaSyAtbi8u-E8RbY_Y0qeyUz4vdPJPGcLwY6c')
        gmap = singleRoute(gmap, file, "uk")
        try:
            gmap.draw("./maps/" + file.replace("./newjsonroutes/", "") + ".html")
        except TypeError:
            print file

    bigboi = gmplot.GoogleMapPlotter(0, 0, 3, 'AIzaSyAtbi8u-E8RbY_Y0qeyUz4vdPJPGcLwY6c')
    bigboi = buildCompound(bigboi, "canada")

    bigboi.draw("canada_combined.html")

    bigboi = gmplot.GoogleMapPlotter(0, 0, 3, 'AIzaSyAtbi8u-E8RbY_Y0qeyUz4vdPJPGcLwY6c')
    bigboi = buildCompound(bigboi, "uk")

    bigboi.draw("janet_combined.html")


def fixJanet(hop):
    # if "noncanarie" not in hop['Hostname']:
    #     if ".ca" in hop['Hostname'][-4:] or "canarie" in hop['Hostname'] or "205.189.32" in hop['Hostname']:
    #         print hop['Hostname']
    #         hop['longitude'] = abs(hop['longitude']) * -1
    #         return hop
    # elif "noncanarie" in hop['Hostname']:
        # return hop

    if "nonjanet" in hop['Hostname']:
        return hop
    elif hop['Hostname'] == 'Camb-rbr1':
        hop['latitude'] = 52.2053
        hop['longitude'] = 0.1218
    elif hop['Hostname'] == 'aber-ban1':
        hop['latitude'] = 57.1497
        hop['longitude'] = 2.0943

    elif hop['Hostname'] == 'aber-ban2':
        hop['latitude'] = 57.1497
        hop['longitude'] = 2.0943

    elif hop['Hostname'] == 'aldess-rbr1':
        hop['latitude'] = hop['latitude']
        hop['longitude'] = hop['longitude']

    elif hop['Hostname'] == 'bathub-rbr1':
        hop['latitude'] = 51.3811
        hop['longitude'] = 2.3590

    elif hop['Hostname'] == 'belfnl-rbr2':
        hop['latitude'] = 54.5973
        hop['longitude'] = 5.9301

    elif hop['Hostname'] == 'birmub-rbr1':
        hop['latitude'] = 52.4862
        hop['longitude'] = 1.8904

    elif hop['Hostname'] == 'bishop-gross-uni':
        hop['latitude'] = 53.2307
        hop['longitude'] = 0.5406

    elif hop['Hostname'] == 'bourss-rbr1':
        hop['latitude'] = 50.7192
        hop['longitude'] = 1.8808

    elif hop['Hostname'] == 'bradcb-rbr1':
        hop['latitude'] = 53.7960
        hop['longitude'] = 1.7594

    elif hop['Hostname'] == 'bradss-sbr2':
        hop['latitude'] = 53.7960
        hop['longitude'] = 1.7594

    elif hop['Hostname'] == 'brisub-rbr1':
        hop['latitude'] = 51.4545
        hop['longitude'] = 2.5879

    elif hop['Hostname'] == 'briswe-rbr1':
        hop['latitude'] = 51.4545
        hop['longitude'] = 2.5879

    elif hop['Hostname'] == 'colcpb-rbr1':
        hop['latitude'] = 51.8959
        hop['longitude'] = 0.8919

    elif hop['Hostname'] == 'dund-ban1':
        hop['latitude'] = 56.4620
        hop['longitude'] = 2.9707

    elif hop['Hostname'] == 'dund-ban3':
        hop['latitude'] = 56.4620
        hop['longitude'] = 2.9707

    elif hop['Hostname'] == 'durham-university':
        hop['latitude'] = 54.7753
        hop['longitude'] = 1.5849

    elif hop['Hostname'] == 'durheb-rbr1':
        hop['latitude'] = 54.7753
        hop['longitude'] = 1.5849

    elif hop['Hostname'] == 'edgehill-cmist':
        hop['latitude'] = 53.5560
        hop['longitude'] = 2.8707

    elif hop['Hostname'] == 'edinat-rbr2':
        hop['latitude'] = 55.9533
        hop['longitude'] = 3.1883

    elif hop['Hostname'] == 'edinhw-rbr2':
        hop['latitude'] = 55.9533
        hop['longitude'] = 3.1883

    elif hop['Hostname'] == 'edinkb-rbr2':
        hop['latitude'] = 55.9533
        hop['longitude'] = 3.1883

    elif hop['Hostname'] == 'edinmb-rbr2':
        hop['latitude'] = 55.9533
        hop['longitude'] = 3.1883

    elif hop['Hostname'] == 'edinqm-rbr2':
        hop['latitude'] = 55.9533
        hop['longitude'] = 3.1883

    elif hop['Hostname'] == 'edinsc-ban1':
        hop['latitude'] = 55.9533
        hop['longitude'] = 3.1883

    elif hop['Hostname'] == 'erdiss-sbr2':
        hop['latitude'] = hop['latitude']
        hop['longitude'] = hop['longitude']

    elif hop['Hostname'] == 'exetec-rbr1':
        hop['latitude'] = 50.7184
        hop['longitude'] = 3.5339

    elif hop['Hostname'] == 'exetue-rbr1':
        hop['latitude'] = 50.7184
        hop['longitude'] = 3.5339

    elif hop['Hostname'] == 'gcu-centre-exec-bldg':
        hop['latitude'] = 55.8642
        hop['longitude'] = 4.2518

    elif hop['Hostname'] == 'glascb-rbr1':
        hop['latitude'] = 55.8642
        hop['longitude'] = 4.2518

    elif hop['Hostname'] == 'glasjw-rbr1':
        hop['latitude'] = 55.8642
        hop['longitude'] = 4.2518

    elif hop['Hostname'] == 'glasss-sbr1':
        hop['latitude'] = 55.8642
        hop['longitude'] = 4.2518

    elif hop['Hostname'] == 'huddbs-rbr1':
        hop['latitude'] = 53.6458
        hop['longitude'] = 1.7850

    elif hop['Hostname'] == 'imperial-college':
        hop['latitude'] = 51.4988
        hop['longitude'] = 0.1749

    elif hop['Hostname'] == 'keele-uni':
        hop['latitude'] = 53.0034
        hop['longitude'] = 2.2721

    elif hop['Hostname'] == 'keellc-rbr1':
        hop['latitude'] = 53.0034
        hop['longitude'] = 2.2721

    elif hop['Hostname'] == 'lancaster-university':
        hop['latitude'] = 54.0466
        hop['longitude'] = 2.8007

    elif hop['Hostname'] == 'lanclu-rbr1':
        hop['latitude'] = 54.0466
        hop['longitude'] = 2.8007

    elif hop['Hostname'] == 'leedaq-rbr1':
        hop['latitude'] = 53.8008
        hop['longitude'] = 1.5491

    elif hop['Hostname'] == 'leedaq-sbr2':
        hop['latitude'] = 53.8008
        hop['longitude'] = 1.5491

    elif hop['Hostname'] == 'leedlm-rbr1':
        hop['latitude'] = 53.8008
        hop['longitude'] = 1.5491

    elif hop['Hostname'] == 'leedlu-rbr1':
        hop['latitude'] = 53.8008
        hop['longitude'] = 1.5491

    elif hop['Hostname'] == 'leeds-trinity-lu':
        hop['latitude'] = 53.8008
        hop['longitude'] = 1.5491

    elif hop['Hostname'] == 'leiccc-rbr3':
        hop['latitude'] = 52.6369
        hop['longitude'] = 1.1398

    elif hop['Hostname'] == 'leicjw-rbr1':
        hop['latitude'] = 52.6369
        hop['longitude'] = 1.1398

    elif hop['Hostname'] == 'lincs4-gw':
        hop['latitude'] = 53.2307
        hop['longitude'] = 0.5406

    elif hop['Hostname'] == 'livebh-rbr1':
        hop['latitude'] = 53.4084
        hop['longitude'] = 2.9916

    elif hop['Hostname'] == 'liverb-rbr1':
        hop['latitude'] = 53.4084
        hop['longitude'] = 2.9916

    elif hop['Hostname'] == 'liverpool-hope-university':
        hop['latitude'] = 53.4084
        hop['longitude'] = 2.9916

    elif hop['Hostname'] == 'londhx-ban1':
        hop['latitude'] = 51.5074
        hop['longitude'] = 0.1278

    elif hop['Hostname'] == 'londhx-ban1':
        hop['latitude'] = 51.5074
        hop['longitude'] = 0.1278

    elif hop['Hostname'] == 'londhx-ban2':
        hop['latitude'] = 51.5074
        hop['longitude'] = 0.1278

    elif hop['Hostname'] == 'londhx-ban3':
        hop['latitude'] = 51.5074
        hop['longitude'] = 0.1278

    elif hop['Hostname'] == 'londhx-sbr1':
        hop['latitude'] = 51.5074
        hop['longitude'] = 0.1278

    elif hop['Hostname'] == 'londic':
        hop['latitude'] = 51.5074
        hop['longitude'] = 0.1278

    elif hop['Hostname'] == 'london-metropolitan-university':
        hop['latitude'] = 51.5074
        hop['longitude'] = 0.1278

    elif hop['Hostname'] == 'londpg-ban1':
        hop['latitude'] = 51.5074
        hop['longitude'] = 0.1278

    elif hop['Hostname'] == 'londpg-sbr2':
        hop['latitude'] = 51.5074
        hop['longitude'] = 0.1278

    elif hop['Hostname'] == 'londpg-sbr2':
        hop['latitude'] = 51.5074
        hop['longitude'] = 0.1278

    elif hop['Hostname'] == 'londsh-rbr2':
        hop['latitude'] = 51.5074
        hop['longitude'] = 0.1278

    elif hop['Hostname'] == 'londtn-ban1':
        hop['latitude'] = 51.5074
        hop['longitude'] = 0.1278

    elif hop['Hostname'] == 'londtt-ban3':
        hop['latitude'] = 51.5074
        hop['longitude'] = 0.1278

    elif hop['Hostname'] == 'londtt-sbr1':
        hop['latitude'] = 51.5074
        hop['longitude'] = 0.1278

    elif hop['Hostname'] == 'londtw-ban1':
        hop['latitude'] = 51.5074
        hop['longitude'] = 0.1278

    elif hop['Hostname'] == 'londtw-sbr2':
        hop['latitude'] = 51.5074
        hop['longitude'] = 0.1278

    elif hop['Hostname'] == 'londtw-sbr2':
        hop['latitude'] = 51.5074
        hop['longitude'] = 0.1278

    elif hop['Hostname'] == 'loughborough-university':
        hop['latitude'] = 52.7721
        hop['longitude'] = 1.2062

    elif hop['Hostname'] == 'lowdss-ban1':
        hop['latitude'] = hop['latitude']
        hop['longitude'] = hop['longitude']

    elif hop['Hostname'] == 'lowdss-sbr1':
        hop['latitude'] = hop['latitude']
        hop['longitude'] = hop['longitude']

    elif hop['Hostname'] == 'manckh-ban1':
        hop['latitude'] = 53.4808
        hop['longitude'] = 2.2426

    elif hop['Hostname'] == 'manckh-ban1':
        hop['latitude'] = 53.4808
        hop['longitude'] = 2.2426

    elif hop['Hostname'] == 'manckh-sbr2':
        hop['latitude'] = 53.4808
        hop['longitude'] = 2.2426

    elif hop['Hostname'] == 'mancrh-rbr1':
        hop['latitude'] = 53.4808
        hop['longitude'] = 2.2426

    elif hop['Hostname'] == 'mancwh-rbr1':
        hop['latitude'] = 53.4808
        hop['longitude'] = 2.2426

    elif hop['Hostname'] == 'middmt-rbr1':
        hop['latitude'] = 54.5742
        hop['longitude'] = 1.2350

    elif hop['Hostname'] == 'middpw-rbr1':
        hop['latitude'] = 54.5742
        hop['longitude'] = 1.2350

    elif hop['Hostname'] == 'mmu':
        hop['latitude'] = 53.4808
        hop['longitude'] = 2.2426

    elif hop['Hostname'] == 'newcastle-university':
        hop['latitude'] = 54.978252
        hop['longitude'] = 1.617780

    elif hop['Hostname'] == 'newcct-rbr1':
        hop['latitude'] = 54.978252
        hop['longitude'] = 1.617780

    elif hop['Hostname'] == 'nottkm-rbr1':
        hop['latitude'] = 52.954784
        hop['longitude'] = 1.158109

    elif hop['Hostname'] == 'oxfoii-rbr1':
        hop['latitude'] = 51.753738
        hop['longitude'] = 1.263460

    elif hop['Hostname'] == 'oxford-university':
        hop['latitude'] = 51.753738
        hop['longitude'] = 1.263460

    elif hop['Hostname'] == 'oxforq-rbr1':
        hop['latitude'] = 51.753738
        hop['longitude'] = 1.263460

    elif hop['Hostname'] == 'presab-rbr1':
        hop['latitude'] = 53.757729
        hop['longitude'] = 2.703440

    elif hop['Hostname'] == 'qub-nl':
        hop['latitude'] = 54.597286
        hop['longitude'] = 5.930120

    elif hop['Hostname'] == 'readdy-rbr1':
        hop['latitude'] = 51.455040
        hop['longitude'] = 0.969090

    elif hop['Hostname'] == 'reading-university-1':
        hop['latitude'] = 51.455040
        hop['longitude'] = 0.969090

    elif hop['Hostname'] == 'readss-rbr1':
        hop['latitude'] = 51.455040
        hop['longitude'] = 0.969090

    elif hop['Hostname'] == 'robert-gordon-university-1':
        hop['latitude'] = 57.1185
        hop['longitude'] = 2.1408

    elif hop['Hostname'] == 'royal-holloway-and-bedford-new-college':
        hop['latitude'] = 51.4257
        hop['longitude'] = 0.5631

    elif hop['Hostname'] == 'royal-vets':
        hop['latitude'] = 51.8098
        hop['longitude'] = 0.2377

    elif hop['Hostname'] == 'salforduni':
        hop['latitude'] = 42.997478
        hop['longitude'] = 80.827477

    elif hop['Hostname'] == 'sheffield-hallam':
        hop['latitude'] = 53.381130
        hop['longitude'] = 1.470085

    elif hop['Hostname'] == 'shefhb-rbr1':
        hop['latitude'] = 53.381130
        hop['longitude'] = 1.470085

    elif hop['Hostname'] == 'stokmb-rbr1':
        hop['latitude'] = 53.002666
        hop['longitude'] = 2.179404

    elif hop['Hostname'] == 'stonss-rbr1':
        hop['latitude'] = hop['latitude']
        hop['longitude'] = hop['longitude']

    elif hop['Hostname'] == 'sundeb-rbr1':
        hop['latitude'] = 54.904449
        hop['longitude'] = 1.381450

    elif hop['Hostname'] == 'surrey-university':
        hop['latitude'] = 51.314758
        hop['longitude'] = 0.559950

    elif hop['Hostname'] == 'teeside-university':
        hop['latitude'] = 51.799883
        hop['longitude'] = 0.045646

    elif hop['Hostname'] == 'telfvm-rbr2':
        hop['latitude'] = 52.6784
        hop['longitude'] = 2.4453

    elif hop['Hostname'] == 'uclan':
        hop['latitude'] = 53.7645
        hop['longitude'] = 2.7084

    elif hop['Hostname'] == 'uni-of-chester':
        hop['latitude'] = 53.1934
        hop['longitude'] = 2.8931

    elif hop['Hostname'] == 'university-creative-arts-1':
        hop['latitude'] = 51.2143
        hop['longitude'] = 0.7988

    elif hop['Hostname'] == 'university-of-bradford':
        hop['latitude'] = 53.7960
        hop['longitude'] = 1.7594

    elif hop['Hostname'] == 'university-of-bristol':
        hop['latitude'] = 51.4545
        hop['longitude'] = 2.5879

    elif hop['Hostname'] == 'university-of-dundee-1':
        hop['latitude'] = 56.4620
        hop['longitude'] = 2.9707

    elif hop['Hostname'] == 'university-of-exeter':
        hop['latitude'] = 50.7184
        hop['longitude'] = 3.5339

    elif hop['Hostname'] == 'university-of-huddersfield':
        hop['latitude'] = 53.6458
        hop['longitude'] = 1.7850

    elif hop['Hostname'] == 'university-of-leeds':
        hop['latitude'] = 53.8008
        hop['longitude'] = 1.5491

    elif hop['Hostname'] == 'university-of-leicester':
        hop['latitude'] = 52.6369
        hop['longitude'] = 1.1398

    elif hop['Hostname'] == 'university-of-lincoln':
        hop['latitude'] = 53.2307
        hop['longitude'] = 0.5406

    elif hop['Hostname'] == 'university-of-northumbria':
        hop['latitude'] = 54.978252
        hop['longitude'] = 1.617780

    elif hop['Hostname'] == 'university-of-sheffield':
        hop['latitude'] = 53.381130
        hop['longitude'] = 1.470085

    elif hop['Hostname'] == 'university-of-st-andrews-1':
        hop['latitude'] = 56.3398
        hop['longitude'] = 2.7967

    elif hop['Hostname'] == 'university-of-the-west-of-england':
        hop['latitude'] = 51.4545
        hop['longitude'] = 2.5879

    elif hop['Hostname'] == 'universityofliverpool':
        hop['latitude'] = 53.4084
        hop['longitude'] = 2.9916

    elif hop['Hostname'] == 'universityofmanchester':
        hop['latitude'] = 53.4808
        hop['longitude'] = 2.2426

    elif hop['Hostname'] == 'warwuw-rbr1':
        hop['latitude'] = 52.2823
        hop['longitude'] = 1.5849

    elif hop['Hostname'] == 'wolvvm-rbr1':
        hop['latitude'] = 52.5870
        hop['longitude'] = 2.1288

    elif hop['Hostname'] == 'worc-rbr2':
        hop['latitude'] = 52.1936
        hop['longitude'] = 2.2216

    hop['longitude'] = -1 * hop['longitude']
    return hop


if __name__ == "__main__":
    ukinput = './traceroutes/*.txt'
    ukoutput = './newjsonroutes/'
    cinput = './Canada/traceroutes/*.txt'
    coutput = './Canada/json/'

    # parseFiles(input, output)
    baseuk = getServers(ukoutput, "uk")
    basecanada = getServers(coutput, "canada")

    mapStuff(baseuk, basecanada)  #
