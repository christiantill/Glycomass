from flask import render_template, redirect, url_for, request
from app import app
from app.forms import GlycomassForm
from app.glycopeptidemass import masscalc

app.debug = True
@app.route('/')
@app.route('/index')
def index():

    return render_template('index.html', title='Home')
@app.route('/about')
def about():

    return render_template('about.html', title='About')

@app.route('/calculate',methods=['GET', 'POST'])
def calculate():
    form = GlycomassForm()
    if form.validate_on_submit():
        Peptide = form.Peptide.data
        Hex = int(form.Hex.data)
        HexNac = int(form.HexNAc.data)
        Fuc = int(form.Fuc.data)
        Sia = int(form.Sia.data)
        Charge = int(form.Charge.data)
        Carbamido= int(form.Carbamido.data)
        Deamidation = int(form.Deamidation.data)
        result = masscalc(Peptide, Hex, HexNac, Fuc, Sia, Charge, Carbamido, Deamidation)
    else:
        result = "None"


    return render_template('mass.html', title='Mass Calculation', form=form, result=result)

