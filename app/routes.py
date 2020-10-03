from flask import render_template, redirect, url_for, request
from app import app
from app.forms import PeptideForm, ProteinForm, GlycanForm
from app.masscalc import peptidemass, proteinmass, glycanmass
import os
import requests
app.debug = False
GA_TRACKING_ID = "UA-179539829-1"
def track_event(category, action, label=None, value=0):
    data = {
        'v': '1',  # API Version.
        'tid': GA_TRACKING_ID,  # Tracking ID / Property ID.
        # Anonymous Client Identifier. Ideally, this should be a UUID that
        # is associated with particular user, device, or browser instance.
        'cid': '555',
        't': 'event',  # Event hit type.
        'ec': category,  # Event category.
        'ea': action,  # Event action.
        'el': label,  # Event label.
        'ev': value,  # Event value, must be an integer
        'ua': 'Opera/9.80 (Windows NT 6.0) Presto/2.12.388 Version/12.14'
    }

    response = requests.post(
        'https://www.google-analytics.com/collect', data=data)

    # If the request fails, this will raise a RequestException. Depending
    # on your application's needs, this may be a non-error and can be caught
    # by the caller.
    response.raise_for_status()

@app.route('/')


@app.route('/index')
def index():
    track_event(
        category='Start',
        action='Opened HP')

    return render_template('index.html', title='Home')


@app.route('/about')
def about():
    track_event(
        category='About',
        action='Opened about')

    return render_template('about.html', title='About')


@app.route('/peptide_calculate', methods=['GET', 'POST'])
def peptide_calculate():
    track_event(
        category='Peptide',
        action='Opened peptide')
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
        track_event(
            category='Peptide',
            action='Submitted peptide')

        return render_template('peptidemass.html', title='Mass Calculation', form=form, monomz=monomz, mostab=mostab,
                               plot_url=plot_url, composition=composition)
    return render_template('peptidemass.html', title='Mass Calculation', form=form)


@app.route('/protein_calculate', methods=['GET', 'POST'])
def protein_calculate():
    track_event(
        category='Protein',
        action='Opened Protein')
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
            track_event(
                category='Protein',
                action='Submitted Protein')
            return render_template('proteinmass.html', title='Mass Calculation', form=form, monomz=monomz,
                                   mostab=mostab, plot_url=plot_url, composition=composition,
                                   cystein_residues=cystein_residues)
        else:
            track_event(
                category='Protein',
                action='Submitted Protein')
            return render_template('proteinmass.html', title='Mass Calculation', form=form, monomz=monomz,
                                   mostab=mostab, plot_url=plot_url, composition=composition)

    return render_template('proteinmass.html', title='Mass Calculation', form=form)


@app.route('/glycan_calculate', methods=['GET', 'POST'])
def glycan_calculate():
    track_event(
        category='Glycan',
        action='Opened Glycan')
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
            track_event(
                category='Glycan',
                action='Negative Ion')
            return render_template('glycan.html', title='Mass Calculation', form=form, negative_ion=negative_ion)
        else:
            result = glycanmass(Hex, HexNac, Fuc, Sia, Charge, Sodium, Modification)
            data = result.split(",")
            monomz = data[0]
            mostab = data[1]
            plot_url = data[2]
            composition = data[3]
            track_event(
                category='Glycan',
                action='Submitted Glycan')
            return render_template('glycan.html', title='Mass Calculation', form=form, monomz=monomz, mostab=mostab,
                                   plot_url=plot_url, composition=composition)

    return render_template('glycan.html', title='Mass Calculation', form=form)
