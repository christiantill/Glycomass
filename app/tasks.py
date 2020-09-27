import sys
import time
from flask import render_template
from rq import get_current_job
from app import create_app, db
from app.masscalc import peptidemass, proteinmass, glycanmass
from app.models import Task, Input, User
app = create_app()
app.app_context().push()

def _set_task_progress(progress):
    job = get_current_job()
    if job:
        job.meta['progress'] = progress
        job.save_meta()
        task = Task.query.get(job.get_id())
        task.user.add_notification('task_progress', {'task_id': job.get_id(),
                                                     'progress': progress})
        if progress >= 100:
            task.complete = True
        db.session.commit()

def calculate_peptidemass(user_id):
    try:
        user=User.query.get(user_id)
        _set_task_progress(0)
        Peptide=Input.Peptide
        Hex=Input.Hex
        HexNac=Input.HexNAc
        Fuc=Input.Fuc
        Sia=Input.Sia
        Charge=Input.Charge
        Carbamido=Input.Charge
        Deamidation=Input.Deamidation
        peptidemass(Peptide, Hex, HexNac, Fuc, Sia, Charge, Carbamido, Deamidation)
        result = peptidemass(Peptide, Hex, HexNac, Fuc, Sia, Charge, Carbamido, Deamidation)
        data = result.split(",")
        monomz = data[0]
        mostab = data[1]
        plot_url = data[2]
        composition = data[3]
        return monomz


