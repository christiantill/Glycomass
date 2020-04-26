from app import db

class Input(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    Peptide =db.Column(db.String())
    Protein = db.Column(db.String())
    Hex = db.Column(db.Float())
    HexNAc = db.Column(db.Float())
    Fuc = db.Column(db.Float())
    Sia = db.Column(db.Float())
    Charge = db.Column(db.Float())
    Deamidation = db.Column(db.Float())
    Carbamido =db.Column(db.Boolean())
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