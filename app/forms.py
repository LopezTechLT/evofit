from flask_wtf import FlaskForm
from wtforms import (
    StringField,
    PasswordField,
    SubmitField,
    SelectField,
    FloatField,
    IntegerField,
    TextAreaField,
    FileField,
    DateField,
)
from wtforms.validators import DataRequired, Email, Length, Optional


class LoginForm(FlaskForm):
    gym_slug = SelectField('Gimnasio', choices=[], validators=[Optional()])
    username = StringField('Usuario', validators=[DataRequired()])
    password = PasswordField('Contraseña', validators=[DataRequired()])
    submit = SubmitField('Entrar')


class RegistrationForm(FlaskForm):
    gym_slug = SelectField('Gimnasio', choices=[], validators=[Optional()])
    username = StringField('Usuario', validators=[DataRequired(), Length(min=4, max=150)])
    email = StringField('Correo electrónico', validators=[DataRequired(), Email()])
    password = PasswordField('Contraseña', validators=[DataRequired(), Length(min=6)])
    phone = StringField('Teléfono', validators=[Optional()])
    age = IntegerField('Edad', validators=[Optional()])
    weight = FloatField('Peso (kg)', validators=[Optional()])
    height = FloatField('Altura (cm)', validators=[Optional()])
    goal = SelectField('Objetivo', choices=[('bajar peso', 'Bajar peso'), ('ganar masa', 'Ganar masa'), ('mantener', 'Mantener')])
    submit = SubmitField('Registrarse')


class ClientForm(FlaskForm):
    name = StringField('Nombre', validators=[DataRequired()])
    email = StringField('Correo electrónico', validators=[DataRequired(), Email()])
    phone = StringField('Teléfono')
    age = IntegerField('Edad', validators=[Optional()])
    weight = FloatField('Peso (kg)', validators=[Optional()])
    height = FloatField('Altura (cm)', validators=[Optional()])
    goal = SelectField('Objetivo', choices=[('bajar peso', 'Bajar peso'), ('ganar masa', 'Ganar masa'), ('mantener', 'Mantener')])
    photo = FileField('Foto')
    submit = SubmitField('Guardar')


class MembershipForm(FlaskForm):
    plan = SelectField('Plan', choices=[('mensual', 'Mensual'), ('quincenal', 'Quincenal'), ('semanal', 'Semanal'), ('anual', 'Anual')])
    end_date = DateField('Fecha de vencimiento', format='%Y-%m-%d', validators=[DataRequired()])
    submit = SubmitField('Guardar')


class PaymentForm(FlaskForm):
    amount = FloatField('Monto', validators=[DataRequired()])
    method = SelectField('Método', choices=[('efectivo', 'Efectivo'), ('tarjeta', 'Tarjeta'), ('transferencia', 'Transferencia')])
    membership_id = SelectField('Membresía', coerce=int, validators=[Optional()])
    description = TextAreaField('Descripción')
    submit = SubmitField('Guardar')


class RoutineForm(FlaskForm):
    name = StringField('Nombre', validators=[DataRequired()])
    category = SelectField('Categoría', choices=[('pecho', 'Pecho'), ('espalda', 'Espalda'), ('pierna', 'Pierna'), ('cardio', 'Cardio')])
    # Se rellena desde el UI interactivo (JSON string)
    exercises = TextAreaField('Ejercicios (JSON)', validators=[Optional()])
    submit = SubmitField('Guardar')


class ProgressForm(FlaskForm):
    weight = FloatField('Peso (kg)', validators=[Optional()])
    measurements = TextAreaField('Medidas (JSON)')
    submit = SubmitField('Guardar')


class GymForm(FlaskForm):
    name = StringField('Nombre del gimnasio', validators=[DataRequired(), Length(min=3, max=150)])
    slug = StringField('Slug (subdominio)', validators=[Optional(), Length(min=2, max=120)])
    plan = SelectField(
        'Plan',
        choices=[('starter', 'Starter'), ('pro', 'Pro'), ('enterprise', 'Enterprise')],
        validators=[DataRequired()]
    )
    submit = SubmitField('Crear gimnasio')


class GymRegistrationForm(FlaskForm):
    gym_name = StringField('Nombre del gimnasio', validators=[DataRequired(), Length(min=3, max=150)])
    gym_slug = StringField('Slug (subdominio)', validators=[Optional(), Length(min=2, max=120)])
    plan = SelectField(
        'Plan',
        choices=[('starter', 'Starter'), ('pro', 'Pro'), ('enterprise', 'Enterprise')],
        validators=[DataRequired()]
    )
    admin_username = StringField('Usuario administrador', validators=[DataRequired(), Length(min=4, max=150)])
    admin_email = StringField('Correo electrónico', validators=[DataRequired(), Email()])
    admin_password = PasswordField('Contraseña', validators=[DataRequired(), Length(min=6)])
    submit = SubmitField('Registrar gimnasio')

