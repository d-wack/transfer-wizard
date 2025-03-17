from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, BooleanField, SubmitField, IntegerField
from wtforms.validators import DataRequired, Length, Optional, NumberRange

class JobForm(FlaskForm):
    name = StringField('Job Name', validators=[DataRequired(), Length(min=1, max=100)])
    description = TextAreaField('Description', validators=[Optional(), Length(max=500)])
    job_type = SelectField('Job Type', choices=[
        ('sftp_transfer', 'SFTP File Transfer'),
        ('sql_to_csv', 'SQL Query to CSV Export')
    ], validators=[DataRequired()])
    schedule = StringField('Schedule (Cron Expression)', 
                           validators=[Optional()], 
                           description="Leave blank for manual execution only")
    is_active = BooleanField('Active', default=True)
    source_credential_id = SelectField('Source Credentials', 
                                    validators=[DataRequired()], 
                                    coerce=int)
    destination_credential_id = SelectField('Destination Credentials', 
                                         validators=[DataRequired()], 
                                         coerce=int)
    submit = SubmitField('Save')

class SftpTransferConfigForm(FlaskForm):
    source_credential_id = SelectField('Source Credentials', 
                                     validators=[DataRequired()], 
                                     coerce=int)
    destination_credential_id = SelectField('Destination Credentials', 
                                          validators=[DataRequired()], 
                                          coerce=int)
    source_directory = StringField('Source Directory', 
                              validators=[DataRequired()],
                              description="Directory on source server to search for files")
    destination_directory = StringField('Destination Directory', 
                                   validators=[DataRequired()],
                                   description="Directory on destination server to upload files to")
    file_pattern = StringField('File Pattern', 
                               validators=[Optional()],
                               default='*',
                               description="Glob pattern to match files (e.g. *.txt)")
    file_rename_pattern = StringField('File Rename Pattern', 
                                     validators=[Optional()],
                                     description="Pattern to rename files during transfer")
    recursive = BooleanField('Search Recursively', default=False)
    create_directories = BooleanField('Create Destination Directories', default=True)
    overwrite_existing = BooleanField('Overwrite Existing Files', default=False)
    delete_after_download = BooleanField('Delete Files After Transfer', default=False)
    max_file_age_days = IntegerField('Maximum File Age (Days)', 
                                    validators=[Optional()], 
                                    default=0,
                                    description="Only transfer files newer than this many days (0 = no limit)")
    max_files_per_run = IntegerField('Maximum Files Per Run',
                                    validators=[Optional(), NumberRange(min=0)],
                                    default=0,
                                    description="Maximum number of files to transfer per run (0 = no limit)")
    fail_on_empty = BooleanField('Fail if No Files Found', default=False)
    preserve_timestamps = BooleanField('Preserve File Timestamps', default=True)
    submit = SubmitField('Save Configuration')

class SqlToCsvConfigForm(FlaskForm):
    source_credential_id = SelectField('Source MSSQL Server', 
                                      validators=[DataRequired()], 
                                      coerce=int)
    destination_credential_id = SelectField('Destination SFTP Server', 
                                           validators=[DataRequired()], 
                                           coerce=int)
    sql_query = TextAreaField('SQL Query', 
                              validators=[DataRequired()],
                              description="SQL query to export data")
    output_file = StringField('Output Filename', 
                              validators=[DataRequired()],
                              description="Name of CSV file to create")
    destination_path = StringField('Destination Path on SFTP', 
                                   validators=[DataRequired()],
                                   description="Path on SFTP server to upload CSV")
    csv_delimiter = StringField('CSV Delimiter', 
                                validators=[Optional()],
                                default=',')
    include_headers = BooleanField('Include Column Headers', default=True)
    submit = SubmitField('Save Configuration')
