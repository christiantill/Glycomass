from flask_wtf import FlaskForm
from wtforms import StringField, FloatField, BooleanField, SubmitField
from wtforms.validators import DataRequired


class GlycomassForm(FlaskForm):
    Peptide = StringField('Peptide', validators=[DataRequired()])
    Hex = FloatField('Hex', validators= None,default=0)
    HexNAc = FloatField('HexNac', validators= None,default=0)
    Fuc = FloatField('Fuc', validators= None,default=0)
    Sia = FloatField('Sia', validators= None,default=0)
    Charge = FloatField('Charge', validators=None,default=0)
    Deamidation = FloatField('Deamidation', validators= None,default=0)
    Carbamido = BooleanField('Carbamido')
    submit = SubmitField('Calculate')