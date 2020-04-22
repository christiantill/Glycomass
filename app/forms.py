from flask_wtf import FlaskForm
from wtforms import StringField, FloatField, BooleanField, SubmitField, RadioField
from wtforms.validators import DataRequired, Length


class PeptideForm(FlaskForm):
    Peptide = StringField('Peptide', validators=[DataRequired(),Length(max=100)])
    Hex = FloatField('Hex', validators= None,default=0)
    HexNAc = FloatField('HexNac', validators= None,default=0)
    Fuc = FloatField('Fuc', validators= None,default=0)
    Sia = FloatField('Sia', validators= None,default=0)
    Charge = FloatField('Charge', validators=None,default=0)
    Deamidation = FloatField('Deamidation', validators= None,default=0)
    Carbamido = BooleanField('Carbamido')
    submit_pep = SubmitField('Calculate')

class ProteinForm(FlaskForm):
    Peptide= StringField('Proteinsequence', validators=[DataRequired()])
    Hex = FloatField('Hex', validators= None,default=0)
    HexNAc = FloatField('HexNac', validators= None,default=0)
    Fuc = FloatField('Fuc', validators= None,default=0)
    Sia = FloatField('Sia', validators= None,default=0)
    Charge = FloatField('Charge', validators=None,default=0)
    Deamidation = FloatField('Deamidation', validators= None,default=0)
    Disulfidebridges = FloatField('Disulfidebridges', validators= None,default=0)
    Resolution = RadioField("Resolution",validators=[DataRequired()], choices= [("low","low"),("medium","medium"),("super high","super high")])
    submit = SubmitField('Calculate')

class GlycanForm(FlaskForm):
    Protein = StringField('Proteinsequence', validators=[DataRequired()])
    Hex = FloatField('Hex', validators= None,default=0)
    HexNAc = FloatField('HexNac', validators= None,default=0)
    Fuc = FloatField('Fuc', validators= None,default=0)
    Sia = FloatField('Sia', validators= None,default=0)
    Charge = FloatField('Charge', validators=None,default=0)
    Deamidation = FloatField('Deamidation', validators= None,default=0)
    Resolution = RadioField("Resolution",validators=[DataRequired()], choices= [("low","5 res"),("medium","10res"),("high res","100 res")])
    submit = SubmitField('Calculate')