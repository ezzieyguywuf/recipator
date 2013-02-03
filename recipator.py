import ConfigParser
from texttable import Texttable
from cmath import e

# This document is protected under the GPLv3. Please see the LICENCE file for
# more info
# TODO implement different measuring systems, default to gallons etc.

class Recipator:
    def __init__(self, filename="recipe1.conf"):
        self.parser = ConfigParser.RawConfigParser()
        self.parser.read(filename)

        self.general_sect = "General"
        self.grain_sect = "Grain Bill"
        self.aroma_sect = "Aroma Hops"
        self.bittering_sect = "Bittering Hops"
        self.ibu_const = 7489
        self.cgrav = 1.00

        self.init_tables()
        self.parse_general()
        self.parse_grains()
        self.parse_hops()
        self.parse_calculated()

    def init_tables(self):
        self.general_table = Texttable()
        self.grain_table = Texttable()
        self.hop_table = Texttable()
        self.hop_table_tinseth = Texttable()
        self.calc_table = Texttable()
        self.hop_shop = Texttable()

    def print_recipe(self):
        print self.general_table.draw()
        print self.calc_table.draw()
        print self.grain_table.draw()
        print self.hop_table.draw()
        #print self.hop_table_tinseth.draw()

    def print_shopping_list(self):
        print self.grain_table.draw()
        print self.hop_shop.draw()

    def parse_general(self):
        self.brew_name = self.parser.get(self.general_sect, "Brew Name")
        self.batch_size = float(self.parser.get(self.general_sect, "Batch Size"))
        self.efficiency = float(self.parser.get(self.general_sect,
                                                "Mash Efficiency").strip())
        self.target_gravity = float(self.parser.get(self.general_sect,
                                                    "Target Gravity").strip())
        self.target_ibu = float(self.parser.get(self.general_sect,
                                                "Target IBU").strip())

        # Calculate total GUs needed in the recipe
        self.total_gus = self.batch_size * self.target_gravity

        self.general_table.add_rows([["Item", "Value"],
                                    ["Brew Name", self.brew_name],
                                    ["Batch Size", self.batch_size],
                                    ["Efficiency (mash)", self.efficiency],
                                    ["Target Gravity", self.target_gravity],
                                     ["Target IBU (GU:BU)", "{0} ({1:.3f})".format(self.target_ibu,
                                                  self.target_gravity/self.target_ibu)]])
    def parse_calculated(self):
        calc_mcu = sum([i[3] for i in self.grain_bill])
        est_srm = 1.4922*(calc_mcu**(0.6859))
        calc_ibu = sum([i[-1] for i in self.hops])
        total_grain = sum([i[1] for i in self.grain_bill])
        total_gravity = self.batch_size * self.target_gravity
        bu_gu = float(calc_ibu) / self.target_gravity

        self.calc_table.add_rows([["Item", "Calc Value"],
                                   ["MCUs", calc_mcu],
                                   ["SRM", est_srm],
                                   ["IBUs", calc_ibu],
                                   ["GU:BU", bu_gu],
                                   ["Total Grain", total_grain],
                                   ["Total Gravity", total_gravity]])

    def parse_grains(self):
        grains = self.parser.options(self.grain_sect)
        # will be [grain, weight (lb), weight (gm), mcu]
        grain_bill = []

        for grain in grains:
            # vals are percentage of fermentables, Nominal GUs, Lovibond
            vals = self.parser.get(self.grain_sect, grain).split(",")
            vals = [float(i.strip()) for i in vals]
            perc, nom, lov = vals

            weight = perc * self.total_gus / (self.efficiency * nom)
            mcu = weight * lov / (self.batch_size)

            grain_bill.append([grain, weight, mcu])

        self.total_weight = sum([i[1] for i in grain_bill])
        self.total_mcu = sum([i[2] for i in grain_bill])

        rows_add = []
        for row in grain_bill:
            perc = row[1]/float(self.total_weight)
            mcu = row[2]
            row[2] = row[1] * 453.592
            row.append(mcu)
            row_add = [perc] + row
            rows_add.append(row_add[0:4])

        self.grain_bill = grain_bill
        header = [["% (weight)", "Grain", "Amount (lb)", "Amount (gm)"]]
        rows_add = header + sorted(rows_add, key= lambda x: x[0], reverse=True)
        self.grain_table.add_rows(rows_add)



    def parse_hops(self):
        hop_names = self.parser.options(self.aroma_sect)
        # will be [boil (min), hop name, AA%, weight (oz), weight (gm), util,
        # IBU contr.]
        hops = []
        hops_tinseth = []

        # Start with the aroma hops
        for hop in hop_names:
            hop_name, boil_time = [i.strip() for i in hop.split("-")]
            boil_time = float(boil_time.strip())
            key = "{0} {1} min".format(hop_name, boil_time)
            # vals are weight, alpha acid % (by weight), utilization, 
            vals = self.parser.get(self.aroma_sect, hop).split(",")
            vals = [float(i.strip()) for i in vals]
            weight, alpha, util = vals

            ibus = weight * util * alpha * self.ibu_const / (self.batch_size *
                                                             self.cgrav)
            f_g_palmer = 1.65 * 0.000125**(self.target_gravity/1000.0)
            f_t_palmer = (1 - e**(-0.04 * boil_time)) / 4.15
            util_palmer = f_g_palmer * f_t_palmer
            ibus_tinseth = weight * util_palmer * alpha * self.ibu_const /\
                          (self.batch_size * self.cgrav)

            # TODO implement Quantities module for better (?) conversion
            weight_gms = weight * 28.3495

            hops.append([boil_time, hop_name, alpha, weight, weight_gms, util,
                         ibus])
            hops_tinseth.append([boil_time, hop_name, alpha, weight, weight_gms,
                                 util, ibus_tinseth])

        aroma_ibus  = sum([i[-1] for i in hops])
        aroma_ibus_tinseth = sum([i[-1] for i in hops_tinseth])

        hop_names = self.parser.options(self.bittering_sect)
        needed_ibu = self.target_ibu - aroma_ibus
        needed_ibu_tinseth = self.target_ibu - aroma_ibus_tinseth

        for hop in hop_names:
            hop_name, boil_time = [i.strip() for i in hop.split("-")]
            # alpha acid % (by weight), utilization, % remaining IBUs
            vals = self.parser.get(self.bittering_sect, hop).split(",")
            vals = [float(i.strip()) for i in vals]
            alpha, util, perc = vals

            ibu = perc * needed_ibu
            weight = self.batch_size * self.cgrav * ibu / (util * alpha *
                                                           self.ibu_const)

            ibu_tinseth = perc * needed_ibu_tinseth
            weight_tinseth = self.batch_size * self.cgrav * ibu_tinseth / \
                             (util * alpha * self.ibu_const)
            # TODO implement Quantities module for better (?) conversion
            weight_gms = weight * 28.3495
            weight_gms_tinseth = weight_tinseth * 28.3495

            hops.append([boil_time, hop_name, alpha, weight, weight_gms, util,
                         ibu])
            hops_tinseth.append([boil_time, hop_name, alpha, weight_tinseth,
                                 weight_gms_tinseth, util, ibu_tinseth])
        hops = sorted(hops, key=lambda x: x[0], reverse=True)
        hops_tinseth = sorted(hops_tinseth, key=lambda x: x[0], reverse=True)

        header = ["Boil (min)", "Hop Name", "Alpha Acid %",
                  "Weight (oz)", "Weight (gm)", "Util.", "IBUs"]
        rows_add = [header] + hops
        self.hop_table.add_rows(rows_add)
        rows_add = [header] + hops_tinseth
        self.hop_table_tinseth.add_rows(rows_add)

        self.hops = hops

        # will be [boil (min), hop name, AA%, weight (oz), weight (gm), util,
        # IBU contr.]
        shopping_list = [["Hop", "AA%", "Weight (oz)", "Weight (gm)"]]
        hop_names = []
        for name in [i[1] for i in self.hops]:
            if not name in hop_names:
                hop_names.append(name)
        for name in hop_names:
            for hop in self.hops:
                if hop[1] == name:
                    alpha = hop[2]*100
                    break
            weight_oz = sum([i[3] for i in self.hops if i[1] == name])
            weight_gm = sum([i[4] for i in self.hops if i[1] == name])
            shopping_list.append([name, "{0:.1f}%".format(alpha), weight_oz, weight_gm])
        self.hop_shop.add_rows(shopping_list)

if __name__=="__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("filename", help="The conf file containing the desired\
                                          recipe attributes")
    parser.add_argument('-s', '--shopping-list', action="store_true",
                        help="Print out a list of ingredients and weights\
                              needed, default off")
    parser.add_argument('-l', '--less', action="store_true",
                        help="remove 'top matter' if you want just the\
                              shopping list")
    args = parser.parse_args()

    myRecipator = Recipator(args.filename)

    if not args.less or (not args.less and not args.shopping_list):
        myRecipator.print_recipe()
    if args.shopping_list:
        print "printing shopping list"
        myRecipator.print_shopping_list()
