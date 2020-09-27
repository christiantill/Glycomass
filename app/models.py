import time

from app import db
import redis
import rq
from flask import current_app
import json


class Input(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    Peptide = db.Column(db.String())
    Protein = db.Column(db.String())
    Hex = db.Column(db.Float())
    HexNAc = db.Column(db.Float())
    Fuc = db.Column(db.Float())
    Sia = db.Column(db.Float())
    Charge = db.Column(db.Float())
    Deamidation = db.Column(db.Float())
    Carbamido = db.Column(db.Boolean())
    Disulfidebridges = db.Column(db.Float())
    Resolution = db.Column(db.String())
    Sodium = db.Column(db.Boolean())
    Modification = db.Column(db.String())

    def __repr__(self):
        return '<id {}>'.format(self.id)


class Result(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    monomz = db.Column(db.String())
    mostab = db.Column(db.String())
    mostab = db.Column(db.String())
    plot_url = db.Column(db.String())
    composition = db.Column(db.String(140))

    user_id = db.Column(db.Integer, db.ForeignKey('input.id'))

    def __repr__(self):
        return '<Result {}>'.format(self.id)


class Task(db.Model):
    id = db.Column(db.String(36), primary_key=True)
    name = db.Column(db.String(128), index=True)
    description = db.Column(db.String(128))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    complete = db.Column(db.Boolean, default=False)

    def get_rq_job(self):
        try:
            rq_job = rq.job.Job.fetch(self.id, connection=current_app.redis)
        except (redis.exceptions.RedisError, rq.exceptions.NoSuchJobError):
            return None
        return rq_job

    def get_progress(self):
        job = self.get_rq_job()
        return job.meta.get('progress', 0) if job is not None else 100


class User(db.Model):
    id = db.Column(db.String(36), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('input.id'))
    notifications = db.relationship('Notification', backref='user',
                                    lazy='dynamic')
    tasks = db.relationship('Task', backref='user', lazy='dynamic')

    def launch_task(self, name, description, *args, **kwargs):
        rq_job = current_app.task_queue.enqueue('app.tasks.' + name, self.id,
                                                *args, **kwargs)
        task = Task(id=rq_job.get_id(), name=name, description=description,
                    user=self)
        db.session.add(task)
        return task

    def get_tasks_in_progress(self):
        return Task.query.filter_by(user=self, complete=False).all()

    def get_task_in_progress(self, name):
        return Task.query.filter_by(name=name, user=self,
                                    complete=False).first()
    def add_notification(self, name, data):
        self.notifications.filter_by(name=name).delete()
        n = Notification(name=name, payload_json=json.dumps(data), user=self)
        db.session.add(n)
        return n

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    timestamp = db.Column(db.Float, index=True, default=time)
    payload_json = db.Column(db.Text)

    def get_data(self):
        return json.loads(str(self.payload_json))
