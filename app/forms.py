from flask_wtf import FlaskForm
from wtforms import StringField, FloatField, BooleanField, SubmitField, RadioField
from wtforms.validators import DataRequired, Length, NumberRange


class PeptideForm(FlaskForm):
    Peptide = StringField('Peptide sequence', validators=[DataRequired(),Length(max=100)])
    Hex = FloatField('Hexose', validators= [NumberRange(max=50)],default=0)
    HexNAc = FloatField('N-acetylhexosamine', validators= [NumberRange(max=50)],default=0)
    Fuc = FloatField('Fucose', validators= [NumberRange(max=50)],default=0)
    Sia = FloatField('Sialic acid', validators= [NumberRange(max=50)],default=0)
    Charge = FloatField('Charge', validators=None,default=0)
    Deamidation = FloatField('Deamidation', validators= [NumberRange(min=0)],default=0)
    Carbamido = BooleanField('Carbamidomethylation')
    submit_pep = SubmitField('Calculate')

class ProteinForm(FlaskForm):
    Peptide= StringField('Protein sequence', validators=[DataRequired(),Length(max=100000)])
    Hex = FloatField('Hexose', validators= [NumberRange(max=100)],default=0)
    HexNAc = FloatField('N-acetylhexosamine', validators= [NumberRange(max=100)],default=0)
    Fuc = FloatField('Fucose', validators= [NumberRange(max=100)],default=0)
    Sia = FloatField('Sialic acid', validators= [NumberRange(max=100)],default=0)
    Charge = FloatField('Charge', validators=None,default=0)
    Deamidation = FloatField('Deamidation', validators= [NumberRange(min=0)],default=0)
    Disulfidebridges = FloatField('Disulfide bridges', validators= None,default=0)
    Resolution = RadioField("Resolution",validators=[DataRequired()], choices= [("low","low resolution"),("medium","medium resolution"),("super high","super high resolution")])
    submit = SubmitField('Calculate')

class GlycanForm(FlaskForm):
    Hex = FloatField('Hexose', validators=[NumberRange(max=50)],default=0)
    HexNAc = FloatField('N-acetylhexosamine', validators= [NumberRange(max=50)],default=0)
    Fuc = FloatField('Fucose', validators= [NumberRange(max=50)],default=0)
    Sia = FloatField('Sialic acid', validators= [NumberRange(max=50)],default=0)
    Charge = FloatField('Charge', validators=None,default=0)
    Sodium = BooleanField('Sodium adduct', validators= None,default=0)
    Modification = RadioField("Modification",validators=[DataRequired()], choices= [("None","No modification"),("Permethyl","Permethylation"),("Peracetly","Peracetylation"),("Label_2AA","2AA-Label"),("Label_2AB","2AB-Label"),("ReducedEnd","Reduced end")])
    submit = SubmitField('Calculate')