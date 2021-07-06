import click
import shutil
import os

from glob import glob
from tqdm import tqdm
from cv2 import imread, imwrite
from pathlib import Path


@click.group()
def tools():
    pass


@tools.command()
@click.option('--input', help='Path to an input directory')
@click.option('--output', help='Path to an output directory')
def generate_segmaps(input, output):
    """
    Ucitava sve datoteke iz direktorijuma 'input' i binarizuje ih
    tako da svaka vrednost veca od 127 postaje 255, a svaka vrednost
    manja ili jednaka sa 127 postaje 0.

    :param input: Direktorijum koji sadrzi grayscale slike koje treba binarizovati.
    :param output: Direktorijum u koji ce biti smesteni rezultati izvrsavanja.
    :return:
    """
    for ipath in tqdm(Path(input).glob('*')):
        fname = ipath.name

        probability_map = imread(str(ipath), -1)
        probability_map[probability_map > 127] = 255
        probability_map[probability_map <= 127] = 0

        imwrite(
            str(Path(output) / fname),
            probability_map
        )


@tools.command()
@click.option('--infile', type=str, help='Fajl u kojem su navedena imena originalna imena slika za koje se straze '
                               'slike iz staging sistema. Nazivi idu jedan po liniji. Moze se navesti i '
                               'proizvoljan deo naziva slike umesto celog naziva.')
@click.option('--stagingdir', type=str, help='Putanja do staging direktorijuma.')
@click.option('--ssuffix', type=str, help='Ekstenzija datoteka iz staging direktorijuma koje se pretrazuju. Zadaje'
                                          'se bez tacke.', default="png")
@click.option('--outfile', type=str, help='Fajl u kojem se nalaze imena svih slika izdvojenih iz staging sistema'
                                'na osnovu imena iz ulaznog fajla.')
@click.option('--strict', is_flag=True, help='Da li nazivi zadati u datoteci moraju biti tvrdo jednaki nazivima '
                                             'datoteka iz zadatog staging direktorijuma.')
def collect_staging_data(infile, outfile, stagingdir, ssuffix, strict):
    """
    Za zadate slike trazi imena istih tih slika u staging direktorijumu (u staging direktorijumu su simbolicki
    linkovi imenovani drugacije u odnosu na originalne slike).

    :param infile: Datoteka u kojoj su navedena imena slika koja se traze. Moze biti ceo naziv ili deo naziva.
                   Zadati string se ne trazi u celoj putanji, samo u nazivu datoteke. Nazive zadati jedan po redu,
                   bez zareza ili slicnih delimitera.
    :param outfile: Datoteka u kojoj ce biti zapisana trazena imena, jedno ime po redu.
    :param stagingdir: Putanja do staging direktorijuma.
    :param ssuffix: Sufiks slika iz staging direktorijuma medju kojima se traze poklapanja (zadaje se bez tacke).
    :return:
    """
    infile = Path(infile)
    if not infile.exists():
        print('Ulazni fajl {} ne postoji.'.format(infile))
        exit(1)

    with open(infile) as f:
        image_names = f.readlines()
        # svi unosi sem pretposlednjeg ce se zavrsiti enterom
        # skida se (izmedju ostalog) enter sa kraja
        image_names = [iname.rstrip() for iname in image_names if not iname.startswith("#")]
        if len(image_names) == 0:
            print(f'Ulazna datoteka {infile} je najverovatnije prazna.')
            exit(1)

    stagingdir = Path(stagingdir)
    if not stagingdir.is_dir() and not stagingdir.exists():
        print('Direktorijum {} ne postoji ili nije direktorijum'.format(stagingdir))
        exit(1)
    staging_images = glob(str(stagingdir / f'*.{ssuffix}'))
    staging_images = [Path(simage) for simage in staging_images]

    if strict:
        print("Strict comparison.")
    else:
        print("Weak comparison.")

    # za svaki zadati naziv iz ulazne datoteke za svaku staging sliku (koja je simbolicki link
    # na sliku) proveriti da li je zadati naziv deo naziva staging slike
    out = list()
    for img_name in image_names:
        print(f"Searching through staging entries for string {img_name}.")
        for simage in staging_images:
            filepath = os.readlink(str(simage))
            # print(f"Looking in {filepath}")
            if strict:
                condition = img_name == Path(filepath).name
            else:
                condition = img_name in Path(filepath).name
            if condition:
                out.append(simage.name)

        # img_out = [simage.name for simage in staging_images if img_name in simage.resolve().name]
        # out.extend(img_out)

    # sacuvaj rezultate, jedan unos, jedna linija
    outfile = Path(outfile)
    if not outfile.exists():
        outfile.touch()
    with open(str(outfile), 'w') as f:
        f.write(f"#total {len(out)}\n")
        [f.write(f"{oline}\n") for oline in out]


@tools.command()
@click.option('--imgfile', type=str, help='Datoteka u kojoj su liniju po liniju navedene slike koje'
                                          'koje treba prekopirati.')
@click.option('--dataset', type=str, help='Na koji se set podataka odnosi imgfile argument.')
@click.option('--indirs', type=str, help="Lista direktorijuma iz kojih se kopiraju rezultati")
@click.option('--outdir', type=str, help="Direktorijum u koji ce biti upisani rezultati")
@click.option('--ext', type=str, default='.png', help="Ekstenzija slika koje se kopiraju iz outdir direktorijuma.")
def collect_data(imgfile, dataset, indirs, outdir, ext):
    """
    Kopiranje zadatih slika iz direktorijuma sa rezultujucim segmentacionim mapama. Treba zadati
    samo putanju do korenskog direktorijuma mreze, a na putanju ce biti automatski dodat string
    '<set podataka>/segmentation_masks'.

    :param imgfile: Datoteka u kojoj su navedeni tacni nazivi slika koje treba prekopirati. Naziv
                    svake slike treba da bude u posebnoj liniji.
    :param dataset: Set podataka za koji je zadat imgfile argument. Moze biti drive ili stare.
    :param indirs:  Direktorijumi rezultata neuronskih mreza u kojima treba trazisiti i iz kojih
                    treba kopirati slike navedene u imgfile.
    :param outdir:  Direktorijum u koji treba kopirati rezultate. U direktorijumu ce biti napravljen
                    poddirektorijum za svaki od zadatih indirs direktorijuma na osnovu poslednje
                    komponente u zadatoj putanji.
    :return:
    """
    with open(imgfile, 'r') as f:
        image_names = [iname.rstrip() for iname in f.readlines() if not iname.startswith("#")]

    dataset = dataset.upper()
    assert dataset in ["DRIVE", "STARE", "CHASE"]

    outdir = Path(outdir)
    assert outdir.is_dir(), f"Izlazni direktorijum ne moze biti na putanji {outdir}"
    outdir.mkdir(exist_ok=True)

    indirs = indirs.split(",")
    for indir in indirs:
        print(f"Obradjujem ulazni direktorijum {indir}.")

        indir = Path(indir)
        assert indir.is_dir() and indir.exists(), \
            f"Direktorijum {indir} ne postoji ili nije direktorijum."

        # za navedeni korenski direktorijum rezultata mreze, napravi direktorijum istog imena
        # u izlaznom direktorijumu
        netdir = outdir / dataset / indir.name
        netdir.mkdir(parents=True, exist_ok=True)
        print(f"Upisujem rezultate izvrsavanja u direktorijum {netdir}.")

        # putanja do direktorijuma mreze iz kojeg se kopiraju slike
        seg_masks_dir = indir / dataset / "segmentation_masks"
        for iname in image_names:
            iname = str(Path(iname).with_suffix('').with_suffix(ext))

            try:
                shutil.copyfile(seg_masks_dir / iname, netdir / iname)
            except FileNotFoundError:
                print(f'Datoteka {seg_masks_dir / iname} nije pronadjena!')


@tools.command()
@click.option('--listfile', type=str, required=True, help='Datoteka u kojoj se nalaze nazivi datoteka koje treba '
                                                          'kopirati.')
@click.option('--indir', type=str, required=True, help='Direktorijum u kojem se traze datoteke ciji su nazivi navedeni '
                                                       'u <listfile>.')
@click.option('--outdir', type=str, required=True, help='Direktorijum u koji se kopiraju datoteke iz direktorijuma '
                                                        '<indir>.')
def copy_data(listfile, indir, outdir):
    """
    Kopiraj sve datoteke cija su imena navedena u listi datoteka iz direktorijuma <indir> u direktorijum <outdir>.

    :param listfile: Datoteka u kojoj se nalaze nazivi datoteka koje treba kopirati.
    :param indir:    Direktorijum u kojem se traze datoteke ciji su nazivi navedeni u <listfile>.
    :param outdir:   Direktorijum u koji se kopiraju datoteke iz direktorijuma <indir>.
    :return:
    """
    with open(listfile, 'r') as f:
        image_names = [iname.rstrip() for iname in f.readlines() if not iname.startswith("#")]

    outdir = Path(outdir)
    # assert outdir.exists() and not outdir.is_dir(), f"Izlazni direktorijum ne moze biti na putanji {outdir}"
    outdir.mkdir(exist_ok=True, parents=True)

    indir = Path(indir)
    assert indir.is_dir() and indir.exists(), \
        f"Direktorijum {indir} ne postoji ili nije direktorijum."

    for iname in image_names:
        # iname = str(Path(iname).with_suffix('').with_suffix(ext))
        oname = Path(iname).name
        outdir_tmp = (outdir / iname).parent
        if not outdir_tmp.exists():
            print(f"Pravim direktorijum {outdir_tmp}.")
            outdir_tmp.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src=indir / iname, dst=outdir_tmp / oname, follow_symlinks=True)


if __name__ == '__main__':
    tools()