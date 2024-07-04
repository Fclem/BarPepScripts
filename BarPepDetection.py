#!/usr/bin/env python

#__==================================== BarPepDetection Script 1.5 ======================================__
#__========== (modified by J. Sippel, J. Weinmann, S. Weis, O. Maiakovska, and E. Locke) ================__


# This script performs identification of barcodes or peptide sequences by flanking constant regions in sequencing data generated by Illumina platforms.
# For each sample, output files are generated which can be further analysed using the BarPep Analysis Script.



#_________________________________________________NECESSARY IMPORTS_______________________________________________________
#

import os
import matplotlib.pyplot as plt
from Bio import SeqIO, Seq
from gzip import open as gzopen
from matplotlib.backends.backend_pdf import PdfPages
import numpy as np
import pandas as pd
import matplotlib.patches as patches
import seaborn as sns
import argparse
import timeit
import copy



#______________________________________________DEFINITION OF ARGUMENTS_____________________________________________________
#

# Set up argument parser
ap = argparse.ArgumentParser()

# Create argument groups
ap._action_groups.pop()
required = ap.add_argument_group("Required Arguments")
optional = ap.add_argument_group("Optional Arguments")
barcode = ap.add_argument_group("Additional Arguments for Barcode Detection")
peptide = ap.add_argument_group("Additional Arguments for Peptide Detection")

# Add arguments to argument groups
required.add_argument("-a", "--mode", required=True, choices=["BC", "PV"], help="Which mode do you want to run the script in? Type 'BC' for barcode detection or 'PV' for peptide detection.")
required.add_argument("-d", "--directory", required=True, help="Give the path to the directory where the sequencing data (gz files) are located.")
required.add_argument("-o", "--outputdir", required=True, help="Give the path to the directory where you want the output files to be saved.")
required.add_argument("-l", "--BCVleft", required=True, help="Give the short flanking oligo sequence at 5' of the barcode location.")
required.add_argument("-r", "--BCVright", required=True, help="Give the short flanking oligo sequence at 3' of the barcode location.")
optional.add_argument("-n", "--BCVloc", type=int, required= False , help = "Give the position of the first expected barcode nt if the read numbering starts with 0.")
optional.add_argument("-m", "--BCVmargin", type=int, required=False, default=5, help="Give the number of nt before and after BCV_loc to search for the barcode (5 is suggested).")
optional.add_argument("-k", "--BCVlocrevcomp", type=int, required=False, help="Give the position of the first expected barcode nt on the reverse complement strand if the read numbering starts with 0.")
optional.add_argument("-p", "--plots", action="store_true", help="Set flag if you want to generate plots showing the quality of your sequencing run.")
optional.add_argument("-w", "--silence", action="store_false", help="Set flag to avoid printouts in the terminal.")
optional.add_argument("-z" "--version", action="version", version="\n"*5+"====== Barcode & Peptide Detection Script 1.5 (modified by J. Sippel, J. Weinmann, S. Weis, O. Maiakovska, and E. Locke) ======\n\n", help="Set flag if you want to print script's version number and exit.")
barcode.add_argument("-v", "--variants", required=False, help="Give the path to the tab-delimited text file that includes unique barcode sequences assigned to one of the cap variants.")
barcode.add_argument("-c", "--contaminations", required=False, help="If you want to check your sequencing data for contaminations, give the path to the tab-delimited text file that includes unique barcode sequences assigned to contaminating cap variants.")
peptide.add_argument("-s", "--BCVsize", type=int, help="Give the length of the insert in nucleotides.")

args = ap.parse_args()



#_________________________________INITIALIZATION OF SILENCE VARIABLE TO AVOID PRINTOUTS_____________________________________
#

silence = args.silence

if silence:
    print("====== BarPepDetection Script 1.5 (modified by J. Sippel, J. Weinmann, S. Weis, O. Maiakovska, and E. Locke) ======\n")



#_________________________________________DEFINITION OF REQUIRED FUNCTIONS__________________________________________________
#

# Function creates a box plot showing the per base sequence quality.
def plot_base_qualities(file, ax=None, limit=100000):
    start = timeit.default_timer()
    res=[]
    c=0
    #Extract the phred score for each base and save it in a data frame
    for record in SeqIO.parse(file, "fastq"):
        score=record.letter_annotations["phred_quality"]
        res.append(score)
        c+=1
        if c>limit:
            break
    df = pd.DataFrame(res)
    l = len(df.T)+1

    #Create the box plot
    if ax==None:
        f,ax=plt.subplots(figsize=(12,5))
    rect = patches.Rectangle((0,0),l,20,linewidth=0,facecolor="r",alpha=.4)
    ax.add_patch(rect)
    rect = patches.Rectangle((0,20),l,8,linewidth=0,facecolor="yellow",alpha=.4)
    ax.add_patch(rect)
    rect = patches.Rectangle((0,28),l,12,linewidth=0,facecolor="g",alpha=.4)
    ax.add_patch(rect)
    df.mean().plot(ax=ax,c="black")
    boxprops = dict(linestyle='-', linewidth=1, color="black")
    df.plot(kind="box", ax=ax, grid=False, showfliers=False,
            color=dict(boxes="black",whiskers="black")  )
    ax.set_xticks(np.arange(0, l, 5))
    ax.set_xticklabels(np.arange(0, l, 5))
    ax.set_xlabel("Position [bp]")
    ax.set_ylabel("Phred Score")
    ax.set_xlim((0,l))
    ax.set_ylim((0,40))
    ax.set_title("Per Base Sequence Quality for "+filename.split(".")[0])

    stop = timeit.default_timer()
    if silence:
        print("\nTime for Per Base Sequence Quality Plot: ", stop - start)
    return



# Function creates a histogram plot showing the per sequence quality scores
def plot_seq_qualities(file, limit=100000):
    start = timeit.default_timer()

    mean_scores=[]
    c=0

    #Get the mean phred score for each sequence and save in a data frame
    for record in SeqIO.parse(file, "fastq"):
        score=record.letter_annotations["phred_quality"]
        mean_scores.append(np.mean(score))
        c+=1
        if c>limit:
            break
    df=pd.DataFrame(mean_scores)

    #Create the histogram plot
    ax=sns.histplot(data=df[0], bins = 35, color="darkblue", edgecolor="darkblue", kde=True, legend=False)
    ax.lines[0].set_color("black")
    ax.set(xlabel="Mean Sequence Quality [Phred Score]")
    ax.set_title("Per Sequence Quality for "+filename.split(".")[0])

    stop = timeit.default_timer()
    if silence:
        print("\nTime for Per Sequence Quality Plot: ", stop - start)
    return


# Function creates a histogram plot showing the sequence length distribution.
def plot_seq_length_dist(file, limit=100000):
    start = timeit.default_timer()
    c=0
    sizes=[]

    #Extract the length of the sequences
    for record in SeqIO.parse(file, "fastq"):
        sizes.append(len(record))
        c+=1
        if c>limit:
            break

    #Create a histogram
    plt.hist(sizes, color="darkblue", edgecolor="black")
    plt.title("Sequence Length Distribution for "+filename.split(".")[0])
    plt.xlabel("Sequence Length [bp]")
    plt.ylabel("Count")
    plt.xticks(np.arange(min(sizes)-2, max(sizes)+3, 1.0))

    stop = timeit.default_timer()
    if silence:
        print("\nTime for Sequence Length Distribution Plot: ", stop - start)
    return


# Function creates a plot showing the per base sequence content
def plot_base_seq_content(file, limit=100000):
    start = timeit.default_timer()
    c=0

    # Initialize variables to store total sequences and total bases
    total_sequences = 0
    total_bases = []

    # Initialize dictionaries for base counts
    base_counts = {"A": [], "T": [], "G": [], "C": []}

    # Open the file and iterate through the sequences to gather all necessary information

    for seq in SeqIO.parse(file, format="fastq"):
        seq_len = len(seq)
        total_sequences += 1
        total_bases.append(seq_len)

        if seq_len > len(base_counts["A"]):
            for key in base_counts:
                base_counts[key].extend([0] * (seq_len - len(base_counts[key])))

        for pos, base in enumerate(seq):
            if base in base_counts:
                base_counts[base][pos] += 1
        c+=1
        if c>limit:
            break


    # Calculate mean bases
    mean_bases = int(np.mean(total_bases))

    # Trim or pad the base counts to the mean bases length
    for key in base_counts:
        base_counts[key] = np.array(base_counts[key][:mean_bases])
        if len(base_counts[key]) < mean_bases:
            base_counts[key] = np.pad(base_counts[key], (0, mean_bases - len(base_counts[key])), "constant")

    # Calculate proportions
    final_counts = {base: (counts / total_sequences * 100) for base, counts in base_counts.items()}

    # Plot base proportions
    plt.plot(final_counts['A'], label="A")
    plt.plot(final_counts['T'], label="T")
    plt.plot(final_counts['G'], label="G")
    plt.plot(final_counts['C'], label="C")
    plt.ylim([0, 100])
    plt.legend(loc="upper right")
    plt.xlabel("Position in Read [bp]")
    plt.ylabel("Proportion of Base [%]")
    plt.title("Sequence Content across all Bases for " + filename.split(".")[0])

    stop = timeit.default_timer()
    if silence:
        print("\nTime for Per Base Sequence Content Plot: ", stop - start)
    return


# Function generates plots using the above-defined functions and saves them on separate pages in a pdf-file
def generate_plots(my_dir, filename, out_dir, gzipped):
    # make output directory
    plot_dir = os.path.join(out_dir, "quality_plots")
    if not os.path.exists(plot_dir):
        os.mkdir(plot_dir)

    file = os.path.join(my_dir, filename)

    # Plot
    """
    There is a weird interaction of gzopen and SeqIO.parse. Workaround below reopens the file for every plot.
    """
    with PdfPages(os.path.join(plot_dir, filename).split(".")[0]+"_Plots.pdf") as pdf:
        # reload file
        if gzipped:
            file = gzopen(os.path.join(my_dir, filename), "rt")
        plot_base_qualities(file)
        pdf.savefig()
        plt.close()
        if silence:
            print("Per Base Sequence Quality Plot generated.")
        # reload file
        if gzipped:
            file = gzopen(os.path.join(my_dir, filename), "rt")
        plot_seq_qualities(file)
        pdf.savefig()
        plt.close()
        if silence:
            print("Per Sequence Quality Plot generated.")
        # reload file
        if gzipped:
            file = gzopen(os.path.join(my_dir, filename), "rt")
        plot_base_seq_content(file)
        pdf.savefig()
        plt.close()
        if silence:
            print("Sequence Content across all Bases Plot generated.")
        # reload file
        if gzipped:
            file = gzopen(os.path.join(my_dir, filename), "rt")
        plot_seq_length_dist(file)
        pdf.savefig()
        plt.close()
        if silence:
            print("Sequence Length Distribution Plot generated.\n")


# Function computes the mean quality of all sequences in a fastq-file
def calculate_mean_quality(file, limit=100000, gzipped=True):
    mean_scores=[]
    c=0
    #Get the mean phred score for each sequence and save in a list
    for record in SeqIO.parse(file, "fastq"):
        score=record.letter_annotations["phred_quality"]
        mean_scores.append(np.mean(score))
        c+=1
        if c>limit:
            break

    # Calculate mean quality
    mean_quality =  np.mean(mean_scores)
    return mean_quality

# Function for detection of barcodes, counting of total reads and reads without constant region, and calculation of sequence length
def barcode_detection(reads, BCV_left, BCV_right, BCV_left_revcomp, BCV_right_revcomp, BCV_size):
    no_constant_region=0
    read_count=0
    result = []
    size=[]

    # For each sequence in the file, the read count is incremented and the sequence is stored as a string in the variable ln
    for line in SeqIO.parse(reads, "fastq"):
        read_count+=1
        if read_count % 10000000 == 0:
            if silence:
                print(str(read_count/1000000) + " mio lines checked")
        size.append(len(line))
        ln = str(line.seq).upper()

        # Search for the the barcode or peptide sequence of the read and store it in the variable BCV: If the constant regions are not found, the next read is analysed
        # find is defined by arguments in brackets, result is the position, where the first argument (first in the bracket) is found
        # A is right constant region, B is left constant region. D and E are the reverse complement constant regions left and right.
        # rfind gives the position of the LAST occurence of the search term
        A=ln.find(BCV_right)
        B=ln.find(BCV_left)
        if A-B==BCV_size+len(BCV_left):
            BCV=ln[B+len(BCV_left):A]
            result.append(BCV)
        else:
            C=ln.rfind(BCV_right)
            if C-B==BCV_size+len(BCV_left):
                BCV=ln[B+len(BCV_left):C]
                result.append(BCV)
            else:
                D=ln.find(BCV_right_revcomp)
                E=ln.find(BCV_left_revcomp)
                if D-E==BCV_size+len(BCV_left_revcomp):
                    BCV=ln[E+len(BCV_left_revcomp):D]
                    result.append(BCV)
                else:
                    F=ln.rfind(BCV_right_revcomp)
                    if F-E==BCV_size+len(BCV_left_revcomp):
                        BCV=ln[E+len(BCV_left_revcomp):F]
                        result.append(BCV)
                    else:
                        no_constant_region+=1
    return result, read_count, no_constant_region, size


# Function for detection of barcodes within a specified search window, counting of total reads and reads without constant region, and calculation of sequence length
def barcode_detection_margin(reads, BCV_left, BCV_right, BCV_loc, BCV_margin, BCV_left_revcomp, BCV_right_revcomp, BCV_loc_revcomp, BCV_size):
    no_constant_region=0
    read_count=0
    result = []
    size=[]

    # For each sequence in the file, the read count is incremented and the sequence is stored as a string in the variable ln
    for line in SeqIO.parse(reads, "fastq"):
        read_count+=1
        if read_count % 10000000 == 0:
            if silence:
                print(str(read_count/1000000) + " mio lines checked")
        size.append(len(line))
        ln = str(line.seq).upper()

        # Search for the the barcode or peptide sequence of the read and store it in the variable BCV: If the constant regions are not found, the next read is analysed
        # find is defined by arguments in brackets, result is the position, where the first argument (first in the bracket) is found
        # A is right constant region, B is left constant region. D and E are the reverse complement constant regions left and right.
        # rfind gives the position of the LAST occurence of the search term
        A=ln.find(BCV_right,BCV_loc-BCV_margin+BCV_size)
        B=ln.find(BCV_left,BCV_loc-BCV_margin-len(BCV_left))
        if A-B==BCV_size+len(BCV_left):
            BCV=ln[B+len(BCV_left):A]
            result.append(BCV)
        else:
            C=ln.rfind(BCV_right,BCV_loc-BCV_margin+BCV_size,BCV_loc+BCV_margin+BCV_size+len(BCV_right))
            if C-B==BCV_size+len(BCV_left):
                BCV=ln[B+len(BCV_left):C]
                result.append(BCV)
            else:
                D=ln.find(BCV_right_revcomp,BCV_loc_revcomp-BCV_margin+BCV_size)
                E=ln.find(BCV_left_revcomp,BCV_loc_revcomp-BCV_margin-len(BCV_left))
                if D-E==BCV_size+len(BCV_left_revcomp):
                    BCV=ln[E+len(BCV_left_revcomp):D]
                    result.append(BCV)
                else:
                    F=ln.rfind(BCV_right_revcomp,BCV_loc_revcomp-BCV_margin+BCV_size,BCV_loc_revcomp+BCV_margin+BCV_size+len(BCV_right))
                    if F-E==BCV_size+len(BCV_left_revcomp):
                        BCV=ln[E+len(BCV_left_revcomp):F]
                        result.append(BCV)
                    else:
                        no_constant_region+=1
    return result, read_count, no_constant_region, size


# Function for labelling unknown sequences
def rename_variants(row):
    if row["Variant"] == row["Barcode"]:
        return "Unknown"
    return row["Variant"]



#________________________________________INITIALIZATION OF VARIABLES WITH ARGUMENTS_________________________________________
#

my_dir = args.directory
out_dir = args.outputdir
BCV_left = args.BCVleft.upper()
BCV_right = args.BCVright.upper()
BCV_loc = args.BCVloc
BCV_margin = args.BCVmargin
BCV_left_revcomp = str(Seq.Seq(BCV_right).reverse_complement()).upper()
BCV_right_revcomp = str(Seq.Seq(BCV_left).reverse_complement()).upper()
BCV_loc_revcomp = args.BCVlocrevcomp
BCV_size = args.BCVsize



#____________________________________________________MODE BARCODE DETECTION_________________________________________________
#

if args.mode == "BC":
    startF = timeit.default_timer()
    if silence:
        print("\n""Barcode Detection Script is running...\n")

    # Variants and their corresponding barcode-sequences are stored in a dictionary called variants: {'barcode':'variant'}
    variants_barcode_file = args.variants
    with open(variants_barcode_file) as temp:
        variants=dict(line.strip().split() for line in temp if line.strip())
    if silence:
        print("\nVariants file: "+variants_barcode_file)


    # If the user gave a path to a tab-delimited text file containing the contaminating barcode sequences, the sequencing data will be checked for contaminations.
    if args.contaminations:
        contaminations_barcode_file = args.contaminations
        if silence:
            print("\nSequencing data will be checked for contaminations.")
            print("Contamination file: "+contaminations_barcode_file)

        # Contaminations and their barcode sequences are stored in a dictionary called contaminationsraw: {'barcode':'contamination'}
        with open(contaminations_barcode_file) as temp:
            contaminationsraw = dict(line.strip().split() for line in temp if line.strip())

        # Remove entries in {contaminationsraw} that are identical with applied barcodes in {variants}
        contaminations = {}
        for c in contaminationsraw:
            if c not in variants:
                d = {c:contaminationsraw[c]}
                contaminations.update(d)


    # If the user did not give a path to a contamination file the sequencing data will not be checked for contaminations
    else:
        if silence:
            print("\nSequencing data will not be checked for contaminations.")
        contaminations = {}


    # The files in the directory are listed
    objects=os.listdir(my_dir)
    j=0
    input_files_gzipped = True
    gz_files = [file for file in objects if file.endswith('.gz')]
    if len(gz_files) == 0:
        input_files_gzipped = False
        gz_files = [file for file in objects if file.endswith('.fastq')]
    if silence:
        print("\n\nThese files will be analyzed:\n")
        # Print the .gz files
        for gz_file in gz_files:
            print(gz_file)


    # iterate through directory
    for filename in objects:

        start = timeit.default_timer()

        if silence:
            print("\n"*10+"Sample being processed: %s" %filename)

        # Sequencing quality data plots are generated if the user asked for them.
        if args.plots:
            # The function generate_plots is called and plots are generated and saved in a pdf-file.
            generate_plots(my_dir, filename, out_dir, input_files_gzipped)

        # The file is processed if it is a gz-file.
        if input_files_gzipped:
            reads = gzopen(os.path.join(my_dir, filename), "rt")
        else:
            reads = os.path.join(my_dir, filename)

        # Length of the barcode is determined
        BCV_size=len(list(variants.keys())[0])
        if silence:
            print("Searching for barcodes...")

        # If the user did not specify the arguments for a defined search window, the default barcode detection function is called
        if not BCV_loc or not BCV_margin or not BCV_loc_revcomp:
            barcode_calc, read_count, no_constant_region, size = barcode_detection(reads, BCV_left, BCV_right, BCV_left_revcomp, BCV_right_revcomp, BCV_size)

        # If the user specified the arguments required to search for the barcode in a defined window, the respective barcode detection method is called
        else:
            barcode_calc, read_count, no_constant_region, size = barcode_detection_margin(reads, BCV_left, BCV_right, BCV_loc, BCV_margin, BCV_left_revcomp, BCV_right_revcomp, BCV_loc_revcomp, BCV_size)

        # Mean size and mean quality are calculated
        mean_size = int(np.mean(size))
        if input_files_gzipped:
            mean_quality = calculate_mean_quality(gzopen(os.path.join(my_dir, filename), "rt"))
        else:
            mean_quality = calculate_mean_quality(reads)


        # A DataFrame with the barcodes, assigned variants (expected or contaminating) and counts is created
        series = pd.DataFrame(barcode_calc).value_counts()
        df = series.to_frame()
        df = df.reset_index()
        df.columns = ["Barcode", "Count"]
        df.insert(1, "Variant", df["Barcode"])
        df = df.replace({"Variant": variants})
        df = df.replace({"Variant": contaminations})

        # Labelling unknown barcodes
        df["Variant"] = df.apply(rename_variants, axis=1)

        # Extracting expected variants
        df["VOI"] = df["Variant"].isin(list(variants.values()))
        df_variants = df.loc[df["VOI"] == True]
        del df_variants["VOI"]

        # Extracting contaminating variants
        df_contaminations = df.loc[df["VOI"] == False]
        del df_contaminations["VOI"]

        # Reset the index
        df_contaminations.reset_index(inplace = True, drop= True)
        # Change the index to start from 1
        df_contaminations.index = df_contaminations.index + 1

        # Convert the variants dictionary to a DataFrame
        barcode_df = pd.DataFrame(list(variants.items()), columns=['Barcode', 'Variant'])
        # Creating a DataFrame with the barcode sequences, variants, and counts
        merged_df = pd.merge(barcode_df, df_variants, on=['Barcode', 'Variant'], how='left')
        # Fill missing counts with 0
        merged_df['Count'] = merged_df['Count'].fillna(0).astype(int)
        # Sort the DataFrame alphabetically by the variant names
        sorted_df_variants = merged_df.sort_values(by='Variant').reset_index(drop=True)
        # Change the index to start from 1
        sorted_df_variants.index = sorted_df_variants.index + 1


        # Counting the number of reads with expected variants, contaminating variants, and unknown variants
        variant_reads = sorted_df_variants["Count"].sum()
        contamination_reads = df_contaminations["Count"].sum()   ##yields number of reads with contaminating and unknown variants
        unknown_variants = df_contaminations.loc[df_contaminations["Variant"] == "Unknown"]["Count"].sum()


        # The log output file is created that includes the total number of reads, the number of recovered reads, of reads with expected variants, with contaminating variants, with unknown variants and the ones where no constant region was found.
        log_output_file=out_dir+filename.split(".")[0]+".log.txt"
        f=open(log_output_file,'w')
        f.write("====== Generated with Barcode & Peptide Detection Script 1.5 ======\n\n")
        f.write("\n"+str(filename.split(".")[0])+"\n\n")
        f.write("\nTotal number of reads: "+str(read_count))
        f.write("\nReads recovered: "+str(read_count-no_constant_region)+" ("+str(round((read_count-no_constant_region)/read_count*100, 2))+"%)"+"\n\nReads with expected variants: "+str(variant_reads)+" ("+str(round(variant_reads/read_count*100, 2))+"%)"+"\nReads with contaminating variants: "+str(contamination_reads-unknown_variants)+" ("+str(round((contamination_reads-unknown_variants)/read_count*100, 2))+"%)\n")
        f.write("Reads with unknown variants: " + str(unknown_variants) + " (" + str(round((unknown_variants) / read_count * 100, 2)) + "%)" + "\nReads with no constant region found: " + str(no_constant_region) + " (" + str(round(no_constant_region / read_count * 100, 2)) + "%)\n")
        f.write("\nMean sequence length: "+str(mean_size)+" bp")
        f.write("\nMean sequence quality: "+str(round(mean_quality, 2)))
        if silence:
            print("\nTotal number of reads: "+str(read_count))
            print("Reads recovered: "+str(read_count-no_constant_region)+" ("+str(round((read_count-no_constant_region)/read_count*100, 2))+"%)")
            print("Reads with expected variants: "+str(variant_reads)+" ("+str(round(variant_reads/read_count*100, 2))+"%)")
            print("Reads with contaminating variants: "+str(contamination_reads-unknown_variants)+" ("+str(round((contamination_reads-unknown_variants)/read_count*100, 2))+"%)")
            print("Reads with unknown variants: "+str(unknown_variants)+" ("+str(round(unknown_variants/read_count*100, 2))+"%)")
            print("Reads with no constant region found: "+str(no_constant_region)+" ("+str(round(no_constant_region/read_count*100, 2))+"%)"+"\n")
            print("Mean sequence length: "+str(mean_size)+" bp")
            print("Mean sequence quality: "+str(round(mean_quality, 2)))
        if "log_output_file" in vars() and log_output_file!="":
            f.write("\n")
            f.close()


        # The output file with the variants and their counts is created.
        variants_output_file=out_dir+filename.split(".")[0]+"_Variants.csv"
        sorted_df_variants.to_csv(variants_output_file)


        # Another output file with the contaminating variants and/or sequences and their respective count is created.
        contaminations_output_file=out_dir+filename.split(".")[0]+"_UnknownVariants.csv"
        df_contaminations.to_csv(contaminations_output_file)


        # Print time for the file
        stop = timeit.default_timer()
        if silence:
            print("\nTime for "+filename.split(".")[0]+": ", stop - start)


    # Print time for the whole directory
    stopF = timeit.default_timer()
    if silence:
        print("\n\nTime for whole directory: ", stopF - startF)


    # The script is completed!
    if silence:
        print("\n\n\n====== Script completed! ======\n\n")



#___________________________________________________MODE PEPTIDE DETECTION___________________________________________________
#

if args.mode == "PV":
    startF = timeit.default_timer()
    if silence:
        print("\n""Peptide Detection Script is running...\n")


    # The files in the directory are listed
    objects=os.listdir(my_dir)
    input_files_gzipped = True
    gz_files = [file for file in objects if file.endswith('.gz')]
    if len(gz_files) == 0:
        input_files_gzipped = False
        gz_files = [file for file in objects if file.endswith('.fastq')]
    if silence:
        print("\n\nThese files will be analyzed:\n")
        # Print the .gz files
        for gz_file in gz_files:
            print(gz_file)


    # iterate through the directory
    for filename in objects:
        start = timeit.default_timer()

        if silence:
            print("\n"*10+"Sample being processed: %s" %filename)

        # Sequencing quality data plots are generated if the user asked for them.
        if args.plots:
            # The function generate_plots is called to generate the plots and save them in a pdf-file.
            generate_plots(my_dir, filename, out_dir, input_files_gzipped)

        # get input file
        if input_files_gzipped:
            reads = gzopen(os.path.join(my_dir, filename), "rt")
        else:
            reads = os.path.join(my_dir, filename)

        # Files in directory are opened with Biopython SeqIO and the function for peptide detection is called
        if silence:
            print("Searching for peptides...")

        # If the user did not specify the arguments for a defined search window, the defualt peptide detection function is called
        if not BCV_loc or not BCV_margin or not BCV_loc_revcomp:
            PV_calc, read_count, no_constant_region, size = barcode_detection(reads, BCV_left, BCV_right, BCV_left_revcomp, BCV_right_revcomp, BCV_size)

        # If the user specified the arguments required to search for the peptide in a defined window, the respective peptide detection method is called
        else:
            PV_calc, read_count, no_constant_region, size = barcode_detection_margin(reads, BCV_left, BCV_right, BCV_loc, BCV_margin, BCV_left_revcomp, BCV_right_revcomp, BCV_loc_revcomp, BCV_size)

        # Mean size and mean quality are calculated
        mean_size = int(np.mean(size))
        # Mean size and mean quality are calculated
        mean_size = int(np.mean(size))
        if input_files_gzipped:
            mean_quality = calculate_mean_quality(gzopen(os.path.join(my_dir, filename), "rt"))
        else:
            mean_quality = calculate_mean_quality(reads)



        # A DataFrame with the peptide sequences and their counts is created
        series = pd.DataFrame(PV_calc).value_counts()
        df_PV = series.to_frame()
        df_PV = df_PV.reset_index()
        df_PV.columns = ["Peptide", "Count"]
        # Change the index to start from 1
        df_PV.index = df_PV.index + 1



        # The log file containing the total number of reads, recovered reads, and mean sequence length and quality is created.
        log_output_file=out_dir+filename.split(".")[0]+".log.txt"
        f=open(log_output_file,'w')
        f.write("====== Generated with Barcode & Peptide Detection Script 1.5 ======\n\n")
        f.write("\n"+str(filename.split(".")[0])+"\n\n")
        f.write("\nTotal number of reads: " + "\t" + str(read_count))
        f.write("\nReads recovered: " + "\t" + str(read_count-no_constant_region)+" ("+str(round((read_count-no_constant_region)/read_count*100, 2))+"%)\n")
        f.write("\nMean sequence length: "+str(mean_size)+" bp")
        f.write("\nMean sequence quality: "+str(round(mean_quality, 2)))
        if silence:
            print("\nTotal number of reads: "+str(read_count))
            print("Reads recovered: "+str(read_count-no_constant_region)+" ("+str(round((read_count-no_constant_region)/read_count*100, 2))+"%)\n")
            print("Mean sequence length: "+str(mean_size)+" bp")
            print("Mean sequence quality: "+str(round(mean_quality, 2)))
        if "log_output_file" in vars() and log_output_file!="":
            f.write("\n")
            f.close()


        # The PV CSV file containing the peptide sequences and their counts is created.
        PV_output_file=out_dir+filename.split(".")[0]+"_PV.csv"
        df_PV.to_csv(PV_output_file)


        # Print time for the file
        stop = timeit.default_timer()
        if silence:
            print("\nTime for "+filename.split(".")[0]+": ", stop - start)


    # Print time for the whole directory
    stopF = timeit.default_timer()
    if silence:
        print("\n\nTime for whole directory: ", stopF - startF)


    # The script is completed!
    if silence:
        print("\n\n\n====== Script completed! ======\n\n")
