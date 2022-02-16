site_id_to_name = {
    "ae": "Ascension Island",
    "an": "Anmyeondo",
    "bi": "Bialystok",
    "br": "Bremen",
    "bu": "Burgos",
    "ci": "Caltech/Pasadena",
    "db": "Darwin",
    "df": "Dryden",
    "et": "East Trout Lake",
    "eu": "Eureka",
    "fc": "Four Corners",
    "gm": "Garmisch",
    "ht": "Arrival Heights",
    "hw": "Harwell",
    "if": "Indianapolis",
    "iz": "Izana",
    "jc": "JPL",
    "jf": "JPL",
    "js": "Saga",
    "jx": "JPL",
    "ka": "Karlsruhe",
    "lh": "Lauder",
    "ll": "Lauder",
    "lr": "Lauder",
    "ma": "Manaus",
    "ni": "Nicosia",
    "ny": "Ny-Alesund",
    "oc": "Lamont",
    "or": "Orleans",
    "pa": "Park Falls",
    "pr": "Paris",
    "ra": "Reunion Island",
    "rj": "Rikubetsu",
    "so": "Sodankyla",
    "tk": "Tsukuba",
    "we": "Jena",
    "wg": "Wollongong",
    "xh": "Xianghe",
    "yk": "Yekaterinburg",
    "zs": "Zugspitze",
}


def get_sites_as_choices(label_fmt='name', include_blank=False):
    if label_fmt == 'name+id':
        choices = [(k, '{} ({})'.format(v, k)) for k, v in site_id_to_name.items()]
    elif label_fmt == 'id':
        choices = [(k, k) for k in site_id_to_name.keys()]
    else:
        choices = [t for t in site_id_to_name.items()]

    if include_blank:
        choices.insert(0, ('', '-'))

    return choices

