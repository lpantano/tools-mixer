"""
Run multiple tools to measure accuracy of isomiRs genome based annotation
"""

from argparse import ArgumentParser
import os
import contextlib

from os.path import exists as is_there
from os.path import abspath as full
from bcbio.provenance import do
from bcbio.utils import safe_makedir
import ann_parser as res

@contextlib.contextmanager
def ch_directory(dir):
    cur_dir = os.getcwd()
    os.chdir(dir)
    yield dir
    os.chdir(cur_dir)


def _stats(ann, bam, fasta, prefix):
    output = prefix + ".tsv"
    if not is_there(output):
        sim_data = res.read_sim_fa(fasta)
        data, counts = res.read_ann(ann)
        mapped = res.read_bam(bam)
        res.print_output(data, counts, sim_data, mapped, output, prefix)
    return output


def _annotate(input, mirbase):
    output = "mirbase.bed"
    cmd = ("bedtools intersect -bed -wo -s -f 0.80 -a"
           " {input} -b {mirbase} >| {output}")
    if not is_there(output):
        do.run(cmd.format(**locals()), "")
    return full(output)


def _star(input, index, mirbase):
    safe_makedir("star")
    with ch_directory("star"):
        output = "star_map.bam"
        cmd = ("STAR --genomeDir {index} --readFilesIN {input}"
               " --outFilterMultimapNmax 50"
               " --outSAMattributes NH HI NM"
               " --alignIntronMax 1")
        cmd_bam = "samtools view -Sbh Aligned.out.sam >| {output}"

        if not is_there("Aligned.out.sam"):
            do.run(cmd.format(**locals()), "")
        if not is_there(output):
            do.run(cmd_bam.format(**locals()), "")

        mirbase_output = _annotate(output, mirbase)
        return (mirbase_output, full(output))


def _bowtie2(input, index, mirbase):
    safe_makedir("bowtie2")
    with ch_directory("bowtie2"):
        output = "bowtie2_map.bam"
        cmd = ("bowtie2 -f -k 50 -L 18 -x {index}"
               " -U {input}"
               " >| hits.sam")
        cmd_bam = "samtools view -Sbh hits.sam >| {output}"

        if not is_there("hits.sam"):
            do.run(cmd.format(**locals()), "")
        if not is_there(output):
            do.run(cmd_bam.format(**locals()), "")

        mirbase_output = _annotate(output, mirbase)
        return (mirbase_output, full(output))


def _hisat(input, index, mirbase):
    safe_makedir("hisat")
    with ch_directory("hisat"):
        output = "hisat_map.bam"
        cmd = ("hisat -f -k 50 -L 18 -x {index}"
               " -U {input}"
               " >| hits.sam")
        cmd_bam = "samtools view -Sbh hits.sam >| {output}"

        if not is_there("hits.sam"):
            do.run(cmd.format(**locals()), "")
        if not is_there(output):
            do.run(cmd_bam.format(**locals()), "")

        mirbase_output = _annotate(output, mirbase)
        return (mirbase_output, full(output))


def _tailor(input, index, mirbase):
    safe_makedir("tailor")
    with ch_directory("tailor"):
        output = "tailor_map.bam"
        cmd = ("tailor  -l 15 map -p {index}"
               " -i {input}"
               " -o hits.sam")
        cmd_bam = "samtools view -Sbh hits.sam >| {output}"

        if not is_there("hits.sam"):
            do.run(cmd.format(**locals()), "")
        if not is_there(output):
            do.run(cmd_bam.format(**locals()), "")

        mirbase_output = _annotate(output, mirbase)
        return (mirbase_output, full(output))


def _bwa_aln(input, index, mirbase):
    safe_makedir("bwa_aln")
    with ch_directory("bwa_aln"):
        output = "bwa_aln_map.bam"
        cmd = ("tailor  -l 15 map -p {index}"
               " -i {input}"
               " -o hits.sam")
        cmd_bam = "samtools view -Sbh hits.sam >| {output}"

        if not is_there("hits.sam"):
            do.run(cmd.format(**locals()), "")
        if not is_there(output):
            do.run(cmd_bam.format(**locals()), "")

        mirbase_output = _annotate(output, mirbase)
        return (mirbase_output, full(output))


def _srnamapper(input, index, mirbase):
    safe_makedir("srnamapper")
    with ch_directory("srnamapper"):
        output = "srnamapper_map.bed"
        cmd = ("sRNAmapper.pl  -i {input} -g  {index}"
               " -s 10 -n 3 -o hits.eland")

        if not is_there("hits.eland"):
            do.run(cmd.format(**locals()), "")
        if not is_there(output):
            with open(output, 'w') as out_handle:
                with open("hits.eland") as in_handle:
                    for line in in_handle:
                        cols = line.strip().split('\t')
                        print >>out_handle, "%s\t%s\t%s\t%s\t1\t%s\t1\t1\t1\t1\t1\t1" % (cols[0], cols[1], int(cols[1]) + len(cols[2]), cols[3], cols[6])

        mirbase_output = _annotate(output, mirbase)
        return (mirbase_output, full(output))


if __name__ == "__main__":
    parser = ArgumentParser(description="Run different tools in simulated fasta file")
    parser.add_argument("--fasta", required=True, help="short reads")
    parser.add_argument("--mirbase", required=True, help="bed file with mirbase annotation")
    parser.add_argument("--star", help="star index")
    parser.add_argument("--bowtie2", help="bowtie2 index")
    parser.add_argument("--hisat", help="hisat index")
    parser.add_argument("--tailor", help="tailor index")
    parser.add_argument("--bwa_aln", help="bwa_aln index")
    parser.add_argument("--srnamapper", help="srnamapper index")
    args = parser.parse_args()

    outputs = {}
    if args.star:
        print "doing STAR"
        outputs.update({"star": _star(full(args.fasta), full(args.star), full(args.mirbase))})
    if args.bowtie2:
        print "doing bowtie2"
        outputs.update({"bowtie2": _bowtie2(full(args.fasta), full(args.bowtie2), full(args.mirbase))})
    if args.hisat:
        print "doing hisat"
        outputs.update({"hisat": _hisat(full(args.fasta), full(args.hisat), full(args.mirbase))})

    if args.tailor:
        print "doing tailor"
        outputs.update({"tailor": _tailor(full(args.fasta), full(args.tailor), full(args.mirbase))})

    if args.bwa_aln:
        print "doing bwa_aln"
        outputs.update({"bwa_aln": _bwa_aln(full(args.fasta), full(args.bwa_aln), full(args.mirbase))})

    if args.srnamapper:
        print "doing srnamapper"
        outputs.update({"srnamapper": _srnamapper(full(args.fasta), full(args.srnamapper), full(args.mirbase))})

    os.remove("summary.tsv") if os.path.exists("summary.tsv") else None
    with open("summary.tsv", 'w') as out_handle:
        out_handle.write(res.H + "\n")
    for tool, stat in outputs.items():
        stat_file = _stats(stat[0], stat[1], args.fasta, tool)
        do.run("cat %s >> summary.tsv" % stat_file, "merging %s" % tool)
