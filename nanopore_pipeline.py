import os
import argparse
import subprocess
import shutil

def run_command(command):
    subprocess.check_call(command, shell=True)

def main(args):
    os.chdir(args.data_directory)
    
    # Setup directories
    directories = ['nanopore_pipeline_out/all_fast5', 'nanopore_pipeline_out/guppy_out', 'nanopore_pipeline_out/mapping', 
                   'nanopore_pipeline_out/pycoqc', 'nanopore_pipeline_out/krakenqc', 'nanopore_pipeline_out/fastq', 
                   'nanopore_pipeline_out/temp']
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
    
    # Aggregate fast5 files
    for file_extension in ['*.fast5', '*.pod5']:
        for filename in subprocess.check_output(f"find . -name '{file_extension}' -not -path './nanopore_pipeline_out/all_fast5/*'", shell=True).decode().splitlines():
            shutil.move(filename, 'nanopore_pipeline_out/all_fast5')
    
    print("############Setup complete############")
    
    os.chdir('nanopore_pipeline_out')
    

#Building the guppy command
    def run_command(disable_sample_sheet, disable_barcode ):
        base_guppy_command =
        f"""guppy_basecaller -i ./all_fast5 -s guppy_out/ --trim_adapters --do_read_splitting
        --compress_fastq --device cuda:0 --min_qscore 7 -c {args.basecalling_model}"""

        # For disabling sample sheet
        if disable_sample_sheet:
            base_guppy_command += "--sample_sheet {args.sample_sheet}"

        # For disabling barcoding
        if disable_barcode:
            base_guppy_command += "--detect_barcodes --enable_trim_barcodes --barcode_kits {args.barcoding_kit}"
        
        subprocess.run(base_guppy_command, shell=True)
    
    print("############Basecalling complete############")
    
    # Organising outputs
    os.chdir('guppy_out/pass')
    for barcode_dir in os.listdir():
        shutil.move(barcode_dir, '../../temp')
    
    os.chdir('../../temp')
    for barcode_dir in os.listdir():
        os.chdir(barcode_dir)
        run_command(f"zcat *.fastq.gz | gzip > ../../fastq/{barcode_dir}.fastq.gz")
        os.chdir('..')
    
    os.chdir('../fastq')
    
    # Activate conda environment
    run_command("conda activate minion")


#Mapping of fastq files using minimap2
    for fastq_file in os.listdir():
        base_name = fastq_file.replace('.fastq.gz', '')
        run_command(f"""
        minimap2 -ax map-ont {args.ref_seq} {fastq_file} | samtools view -S -b - | samtools sort - -o ../mapping/{base_name}.bam
        """)
        run_command(f"samtools index ../mapping/{base_name}.bam")
    
    print("############Mapping complete############")
    
    # pycoQC report generation steps
    run_command("conda activate pycoQC")
    
    for fastq_file in os.listdir():
        base_name = fastq_file.replace('.fastq.gz', '')
        run_command(f"""
        pycoQC -f ../guppy_out/sequencing_summary.txt -a ../mapping/{base_name}.bam -o ../pycoqc/{base_name}.pycoqc.html
        """)
    
    os.chdir('../pycoqc')
    # (Additional pycoQC operations here...)
    
    print("############PycoQC complete############")
    
    # Kraken reports
    os.chdir('../fastq')
    run_command("conda activate kraken2")
    
    for fastq_file in os.listdir():
        run_command(f"kraken2_client --host-ip 10.18.0.25 --sequence {fastq_file} --report ../krakenqc/{fastq_file}.kreport > ../krakenqc/{fastq_file}.kraken")
    
    os.chdir('../krakenqc')
    # (Additional Kraken operations here...)
    
    print("############Kraken complete############")
    
    # Cleanup
    os.chdir('../')
    shutil.rmtree('temp')
    
    print("############Clean-up complete############")
    
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='A script for basecalling, demultiplexing, mapping, and QC.')
    parser.add_argument('data_directory', help='MinKNOW experiment root directory')
    parser.add_argument('exp_name', help='Experiment name')
    parser.add_argument('barcoding_kit', help='Barcoding kit')
    parser.add_argument('sample_sheet', help='CSV sample sheet absolute path')
    parser.add_argument('ref_seq', help='FASTA reference sequence absolute path')
    parser.add_argument('basecalling_model', help='Basecalling model')
    parser.add_argument('--disable_sample_sheet', action='false', help='Disable requirement for sample sheet.')
    parser.add_argument('--disable_barcode', action='false', help='Disable requirement for sample sheet.')
    
    args = parser.parse_args()
    main(args)
