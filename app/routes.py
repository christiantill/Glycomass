from flask import render_template, redirect, url_for, request, send_file, jsonify, abort, send_from_directory
from werkzeug.utils import secure_filename

from app import app
from app.forms import PeptideForm, ProteinForm, GlycanForm
from app.masscalc import peptidemass, proteinmass, glycanmass
from .helper import *
from .redis_resc import redis_conn, redis_queue
from .rd_func import *
from rq.job import Job
app.debug = False
GA_TRACKING_ID = "UA-179539829-1"
UPLOAD_FOLDER = "uploads"
BUCKET = "glycomass"
import os


@app.route('/')
@app.route('/index')
def index():
    return render_template('index.html', title='Home')


@app.route('/about')
def about():

    return render_template('about.html', title='About')


@app.route('/glycan_identifier', methods=['GET', 'POST'])
def glyan_identifier():
    if request.method == "POST":
        # A
        if "user_file" not in request.files:
            return "No user_file key in request.files"

        # B
        file = request.files["user_file"]

        """
            These attributes are also available

            file.filename               # The actual name of the file
            file.content_type
            file.content_length
            file.mimetype

        """

        # C.
        if file.filename == "":
            return "Please select a file"

        # D.
        if file:
            file.filename = secure_filename(file.filename)
            output = upload_file_to_s3(file, app.config["S3_BUCKET"])
            return str(output)

        else:
            return redirect("/")
    return render_template('identifier.html', title='Glycan Identifier')


@app.route('/peptide_calculate', methods=['GET', 'POST'])
def peptide_calculate():
    form = PeptideForm()
    if form.validate_on_submit():
        Peptide = form.Peptide.data
        Hex = int(form.Hex.data)
        HexNac = int(form.HexNAc.data)
        Fuc = int(form.Fuc.data)
        Sia = int(form.Sia.data)
        Charge = int(form.Charge.data)
        Carbamido = int(form.Carbamido.data)
        Deamidation = int(form.Deamidation.data)
        result = peptidemass(Peptide, Hex, HexNac, Fuc, Sia, Charge, Carbamido, Deamidation)
        data = result.split(",")
        monomz = data[0]
        mostab = data[1]
        plot_url = data[2]
        composition = data[3]

        return render_template('peptidemass.html', title='Mass Calculation', form=form, monomz=monomz, mostab=mostab,
                               plot_url=plot_url, composition=composition)
    return render_template('peptidemass.html', title='Mass Calculation', form=form)


@app.route('/protein_calculate', methods=['GET', 'POST'])
def protein_calculate():
    form = ProteinForm()
    if form.validate_on_submit():
        Peptide = form.Peptide.data
        Hex = int(form.Hex.data)
        HexNac = int(form.HexNAc.data)
        Fuc = int(form.Fuc.data)
        Sia = int(form.Sia.data)
        Charge = int(form.Charge.data)
        resolution = form.Resolution.data
        Deamidation = int(form.Deamidation.data)
        Disulfidebridges = int(form.Disulfidebridges.data)
        result = proteinmass(Peptide, Hex, HexNac, Fuc, Sia, Charge, Deamidation, Disulfidebridges, resolution)
        data = result.split(",")
        monomz = data[0]
        mostab = data[1]
        plot_url = data[2]
        composition = data[3]
        countC = Peptide.count('C')
        if (countC < (Disulfidebridges * 2)):
            cystein_residues = True

            return render_template('proteinmass.html', title='Mass Calculation', form=form, monomz=monomz,
                                   mostab=mostab, plot_url=plot_url, composition=composition,
                                   cystein_residues=cystein_residues)
        else:

            return render_template('proteinmass.html', title='Mass Calculation', form=form, monomz=monomz,
                                   mostab=mostab, plot_url=plot_url, composition=composition)

    return render_template('proteinmass.html', title='Mass Calculation', form=form)


@app.route('/glycan_calculate', methods=['GET', 'POST'])
def glycan_calculate():
    form = GlycanForm()
    if form.validate_on_submit():
        Hex = int(form.Hex.data)
        HexNac = int(form.HexNAc.data)
        Fuc = int(form.Fuc.data)
        Sia = int(form.Sia.data)
        Charge = int(form.Charge.data)
        Modification = form.Modification.data
        Sodium = form.Sodium.data
        if (Sodium == True and Charge <= 0):
            negative_ion = True

            return render_template('glycan.html', title='Mass Calculation', form=form, negative_ion=negative_ion)
        else:
            result = glycanmass(Hex, HexNac, Fuc, Sia, Charge, Sodium, Modification)
            data = result.split(",")
            monomz = data[0]
            mostab = data[1]
            plot_url = data[2]
            composition = data[3]

            return render_template('glycan.html', title='Mass Calculation', form=form, monomz=monomz, mostab=mostab,
                                   plot_url=plot_url, composition=composition)

    return render_template('glycan.html', title='Mass Calculation', form=form)

@app.route("/enqueue", methods=["POST", "GET"])
def enqueue():
    """Enqueues a task into redis queue to be processes.
    Returns the job_id."""
    if request.method == "GET":
        query_param = request.args.get("external_id")
        if not query_param:
            abort(
                404,
                description=(
                    "No query parameter external_id passed. "
                    "Send a value to the external_id query parameter."
                ),
            )
        data = {"external_id": query_param}
    if request.method == "POST":
        data = request.json

    job = redis_queue.enqueue(some_long_function, data)
    return jsonify({"job_id": job.id})


@app.route("/check_status")
def check_status():
    """Takes a job_id and checks its status in redis queue."""
    job_id = request.args["job_id"]

    try:
        job = Job.fetch(job_id, connection=redis_conn)
    except Exception as exception:
        abort(404, description=exception)

    return jsonify({"job_id": job.id, "job_status": job.get_status()})


@app.route("/get_result")
def get_result():
    """Takes a job_id and returns the job's result."""
    job_id = request.args["job_id"]

    try:
        job = Job.fetch(job_id, connection=redis_conn)
    except Exception as exception:
        abort(404, description=exception)

    if not job.result:
        abort(
            404,
            description=f"No result found for job_id {job.id}. Try checking the job's status.",
        )
    return jsonify(job.result)

@app.route('/sitemap.xml')
def sitemap():
    return send_from_directory(os.path.join(app.root_path, 'static'), 'sitemap.xml')
