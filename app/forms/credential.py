from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, SubmitField, IntegerField, TextAreaField, PasswordField, HiddenField, BooleanField
from wtforms.validators import DataRequired, Length, Optional, NumberRange

class CredentialForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(min=1, max=100)])
    description = TextAreaField('Description', validators=[Optional(), Length(max=500)])
    credential_type = SelectField('Type', choices=[
        ('sftp', 'SFTP Server'),
        ('mssql', 'Microsoft SQL Server')
    ], validators=[DataRequired()])
    submit = SubmitField('Save')

class SftpCredentialForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(min=1, max=100)])
    description = TextAreaField('Description', validators=[Optional(), Length(max=500)])
    credential_type = HiddenField('Type', default='sftp')
    host = StringField('Host', validators=[DataRequired()])
    port = IntegerField('Port', validators=[DataRequired(), NumberRange(min=1, max=65535)], default=22)
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password (leave blank to keep unchanged)', validators=[Optional()])
    private_key = TextAreaField('Private Key (leave blank to keep unchanged)', validators=[Optional()])
    private_key_passphrase = PasswordField('Private Key Passphrase (leave blank to keep unchanged)', validators=[Optional()])
    base_dir = StringField('Base Directory', validators=[Optional()], default='/')
    disable_host_key_checking = BooleanField('Disable Host Key Checking', default=False)
    submit = SubmitField('Save')

class MssqlCredentialForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(min=1, max=100)])
    description = TextAreaField('Description', validators=[Optional(), Length(max=500)])
    credential_type = HiddenField('Type', default='mssql')
    server = StringField('Server', validators=[DataRequired()])
    hostname = StringField('Hostname', validators=[DataRequired()])  # Alias for server
    database = StringField('Database', validators=[DataRequired()])
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password (leave blank to keep unchanged)', validators=[Optional()])
    port = IntegerField('Port', validators=[DataRequired(), NumberRange(min=1, max=65535)], default=1433)
    encrypt = SelectField('Encryption', choices=[
        ('yes', 'Yes (Encrypted)'),
        ('no', 'No (Unencrypted)'),
        ('strict', 'Strict (Validate Certificate)')
    ], default='yes')
    trust_server_certificate = BooleanField('Trust Server Certificate', default=False)
    submit = SubmitField('Save')
