from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models.credential import Credential
from app.forms.credential import CredentialForm, SftpCredentialForm, MssqlCredentialForm
from app.models.job import Job
from loguru import logger

# Import the utility clients, with fallbacks if dependencies are not installed
try:
    from app.utils.sftp_utils import SftpClient
except ImportError:
    logger.warning("Could not import SftpClient - SFTP functionality will be limited")
    SftpClient = None

try:
    from app.utils.mssql_utils import MssqlClient
except ImportError:
    logger.warning("Could not import MssqlClient - MSSQL functionality will be limited")
    MssqlClient = None

credentials_bp = Blueprint('credentials', __name__)

@credentials_bp.route('/')
@login_required
def index():
    credentials = Credential.query.filter_by(user_id=current_user.id).order_by(Credential.name).all()
    return render_template('credentials/index.html', title='Credentials', credentials=credentials)

@credentials_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    # Create both form types for the template
    credential_form = CredentialForm()
    sftp_form = SftpCredentialForm()
    mssql_form = MssqlCredentialForm()
    
    # Determine which credential type is being processed
    credential_type = request.form.get('credential_type', request.args.get('type', 'sftp'))
    
    if request.method == 'POST':
        # Process the form submission based on credential type
        if credential_type == 'sftp' and sftp_form.validate_on_submit():
            # Create the base credential
            credential = Credential(
                name=sftp_form.name.data if hasattr(sftp_form, 'name') else request.form.get('name'),
                description=sftp_form.description.data if hasattr(sftp_form, 'description') else request.form.get('description', ''),
                credential_type='sftp',
                user_id=current_user.id
            )
            
            # Set SFTP-specific configuration
            sftp_config = {
                'host': sftp_form.host.data,
                'port': sftp_form.port.data,
                'username': sftp_form.username.data,
                'password': sftp_form.password.data if sftp_form.password.data else '',
                'private_key': getattr(sftp_form, 'private_key', {}).data if hasattr(sftp_form, 'private_key') else '',
                'private_key_passphrase': getattr(sftp_form, 'private_key_passphrase', {}).data if hasattr(sftp_form, 'private_key_passphrase') else '',
                'base_dir': getattr(sftp_form, 'base_dir', {}).data if hasattr(sftp_form, 'base_dir') else '',
                'disable_host_key_checking': getattr(sftp_form, 'disable_host_key_checking', {}).data if hasattr(sftp_form, 'disable_host_key_checking') else False
            }
            
            credential.set_credentials(sftp_config)
            db.session.add(credential)
            db.session.commit()
            
            flash('SFTP credential created successfully!', 'success')
            return redirect(url_for('credentials.view', credential_id=credential.id))
            
        elif credential_type == 'mssql' and mssql_form.validate_on_submit():
            # Create the base credential
            credential = Credential(
                name=mssql_form.name.data if hasattr(mssql_form, 'name') else request.form.get('name'),
                description=mssql_form.description.data if hasattr(mssql_form, 'description') else request.form.get('description', ''),
                credential_type='mssql',
                user_id=current_user.id
            )
            
            # Set MSSQL-specific configuration
            mssql_config = {
                'server': mssql_form.server.data,
                'database': mssql_form.database.data,
                'username': mssql_form.username.data,
                'password': mssql_form.password.data if mssql_form.password.data else '',
                'port': mssql_form.port.data,
                'encrypt': getattr(mssql_form, 'encrypt', {}).data if hasattr(mssql_form, 'encrypt') else 'yes',
                'trust_server_certificate': getattr(mssql_form, 'trust_server_certificate', {}).data if hasattr(mssql_form, 'trust_server_certificate') else False
            }
            
            credential.set_credentials(mssql_config)
            db.session.add(credential)
            db.session.commit()
            
            flash('MSSQL credential created successfully!', 'success')
            return redirect(url_for('credentials.view', credential_id=credential.id))
    
    # For GET requests, render the form
    return render_template('credentials/create.html', 
                          title='Create Credential', 
                          form=credential_form,
                          sftp_form=sftp_form,
                          mssql_form=mssql_form,
                          credential_type=credential_type)

@credentials_bp.route('/<int:credential_id>/configure', methods=['GET', 'POST'])
@login_required
def configure(credential_id):
    credential = Credential.query.get_or_404(credential_id)
    
    # Check ownership
    if credential.user_id != current_user.id:
        flash('You do not have permission to access this credential', 'danger')
        return redirect(url_for('credentials.index'))
    
    # Select the appropriate form based on credential type
    if credential.credential_type == 'sftp':
        form = SftpCredentialForm()
        
        if request.method == 'GET':
            creds = credential.get_credentials()
            form.host.data = creds.get('host', '')
            form.port.data = creds.get('port', 22)
            form.username.data = creds.get('username', '')
            form.password.data = '' # Don't show existing password
            form.private_key.data = creds.get('private_key', '')
            form.private_key_pass.data = '' # Don't show existing passphrase
        
        if form.validate_on_submit():
            # Get existing credentials to preserve password/key if not changed
            creds = credential.get_credentials()
            
            # Update fields
            creds['host'] = form.host.data
            creds['port'] = form.port.data
            creds['username'] = form.username.data
            
            # Only update password if provided
            if form.password.data:
                creds['password'] = form.password.data
            
            # Only update private key if provided
            if form.private_key.data:
                creds['private_key'] = form.private_key.data
            
            # Only update private key passphrase if provided
            if form.private_key_pass.data:
                creds['private_key_pass'] = form.private_key_pass.data
            
            credential.set_credentials(creds)
            db.session.commit()
            
            flash('SFTP credentials updated successfully!', 'success')
            return redirect(url_for('credentials.index'))
    
    elif credential.credential_type == 'mssql':
        form = MssqlCredentialForm()
        
        if request.method == 'GET':
            creds = credential.get_credentials()
            form.server.data = creds.get('server', '')
            form.database.data = creds.get('database', '')
            form.username.data = creds.get('username', '')
            form.password.data = '' # Don't show existing password
            form.port.data = creds.get('port', 1433)
        
        if form.validate_on_submit():
            # Get existing credentials to preserve password if not changed
            creds = credential.get_credentials()
            
            # Update fields
            creds['server'] = form.server.data
            creds['database'] = form.database.data
            creds['username'] = form.username.data
            creds['port'] = form.port.data
            
            # Only update password if provided
            if form.password.data:
                creds['password'] = form.password.data
            
            credential.set_credentials(creds)
            db.session.commit()
            
            flash('MSSQL credentials updated successfully!', 'success')
            return redirect(url_for('credentials.index'))
    
    return render_template(
        f'credentials/configure_{credential.credential_type}.html',
        title=f'Configure {credential.name}',
        credential=credential,
        form=form
    )

@credentials_bp.route('/<int:credential_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(credential_id):
    credential = Credential.query.get_or_404(credential_id)
    
    # Check ownership
    if credential.user_id != current_user.id:
        flash('You do not have permission to access this credential', 'danger')
        return redirect(url_for('credentials.index'))
    
    logger.debug(f"Editing credential ID {credential_id} of type {credential.credential_type}")
    
    # Use the appropriate form based on credential type
    if credential.credential_type == 'sftp':
        form = SftpCredentialForm()
        
        if request.method == 'GET':
            form.name.data = credential.name
            form.description.data = credential.description
            
            # Get credential configuration
            config = credential.get_credentials()
            form.host.data = config.get('host', '')
            form.port.data = config.get('port', 22)
            form.username.data = config.get('username', '')
            form.base_dir.data = config.get('base_dir', '/')
            form.disable_host_key_checking.data = config.get('disable_host_key_checking', False)
            # Don't populate password or private key for security
            
        if form.validate_on_submit():
            credential.name = form.name.data
            credential.description = form.description.data
            
            # Get the existing credentials to update
            config = credential.get_credentials()
            
            # Update with new values
            config['host'] = form.host.data
            config['port'] = form.port.data
            config['username'] = form.username.data
            config['base_dir'] = form.base_dir.data
            config['disable_host_key_checking'] = form.disable_host_key_checking.data
            
            # Only update password if provided
            if form.password.data:
                config['password'] = form.password.data
                
            # Only update private key if provided
            if form.private_key.data:
                config['private_key'] = form.private_key.data
                
            # Only update private key passphrase if provided
            if form.private_key_passphrase.data:
                config['private_key_passphrase'] = form.private_key_passphrase.data
                
            credential.set_credentials(config)
            db.session.commit()
            
            flash('SFTP credential updated successfully!', 'success')
            return redirect(url_for('credentials.index'))
            
    elif credential.credential_type == 'mssql':
        form = MssqlCredentialForm()
        
        if request.method == 'GET':
            form.name.data = credential.name
            form.description.data = credential.description
            
            # Get credential configuration
            config = credential.get_credentials()
            form.server.data = config.get('server', '')
            form.hostname.data = config.get('server', '')  # Same as server
            form.database.data = config.get('database', '')
            form.username.data = config.get('username', '')
            form.port.data = config.get('port', 1433)
            form.encrypt.data = config.get('encrypt', 'yes')
            form.trust_server_certificate.data = config.get('trust_server_certificate', False)
            # Don't populate password for security
            
        if form.validate_on_submit():
            credential.name = form.name.data
            credential.description = form.description.data
            
            # Get the existing credentials to update
            config = credential.get_credentials()
            
            # Update with new values
            config['server'] = form.server.data
            config['database'] = form.database.data
            config['username'] = form.username.data
            config['port'] = form.port.data
            config['encrypt'] = form.encrypt.data
            config['trust_server_certificate'] = form.trust_server_certificate.data
            
            # Only update password if provided
            if form.password.data:
                config['password'] = form.password.data
                
            credential.set_credentials(config)
            db.session.commit()
            
            flash('MSSQL credential updated successfully!', 'success')
            return redirect(url_for('credentials.index'))
    else:
        # Generic form for unknown credential types
        form = CredentialForm()
        
        if request.method == 'GET':
            form.name.data = credential.name
            form.description.data = credential.description
            form.credential_type.data = credential.credential_type
        
        if form.validate_on_submit():
            # Check if credential type is changing
            type_changed = credential.credential_type != form.credential_type.data
            
            credential.name = form.name.data
            credential.description = form.description.data
            
            if type_changed:
                # Reset credentials if type is changing
                credential.credential_type = form.credential_type.data
                credential.set_credentials(Credential.get_default_config(form.credential_type.data))
            
            db.session.commit()
            
            flash('Credential updated successfully!', 'success')
            
            if type_changed:
                return redirect(url_for('credentials.configure', credential_id=credential.id))
            return redirect(url_for('credentials.index'))
    
    return render_template('credentials/edit.html', title='Edit Credential', form=form, credential=credential)

@credentials_bp.route('/<int:credential_id>/delete', methods=['POST'])
@login_required
def delete(credential_id):
    credential = Credential.query.get_or_404(credential_id)
    
    # Check ownership
    if credential.user_id != current_user.id:
        flash('You do not have permission to access this credential', 'danger')
        return redirect(url_for('credentials.index'))
    
    # Check if any jobs are using this credential
    jobs_using_credential = Job.query.filter(
        (Job.source_credential_id == credential.id) | 
        (Job.destination_credential_id == credential.id)
    ).all()
    
    if jobs_using_credential:
        job_names = ', '.join([job.name for job in jobs_using_credential])
        flash(f'Cannot delete: Credential is being used by the following jobs: {job_names}', 'danger')
        return redirect(url_for('credentials.index'))
    
    db.session.delete(credential)
    db.session.commit()
    
    flash('Credential deleted successfully!', 'success')
    return redirect(url_for('credentials.index'))

@credentials_bp.route('/<int:credential_id>')
@login_required
def view(credential_id):
    credential = Credential.query.get_or_404(credential_id)
    
    # Check ownership
    if credential.user_id != current_user.id:
        flash('You do not have permission to access this credential', 'danger')
        return redirect(url_for('credentials.index'))
    
    # Get jobs using this credential
    jobs_using_credential = Job.query.filter(
        (Job.source_credential_id == credential.id) | 
        (Job.destination_credential_id == credential.id)
    ).all()
    
    return render_template('credentials/view.html', 
                           title=credential.name, 
                           credential=credential, 
                           jobs=jobs_using_credential)

@credentials_bp.route('/<int:credential_id>/test')
@login_required
def test(credential_id):
    credential = Credential.query.get_or_404(credential_id)
    
    # Check ownership
    if credential.user_id != current_user.id:
        logger.warning(f"User {current_user.id} attempted to test credential {credential_id} belonging to user {credential.user_id}")
        return jsonify({'success': False, 'message': 'You do not have permission to access this credential'})
    
    logger.info(f"Testing credential ID {credential_id} ({credential.name}) of type {credential.credential_type}")
    
    try:
        # Get credential configuration
        config = credential.get_credentials()
        
        # Test the connection based on credential type
        if credential.credential_type == 'sftp':
            logger.debug(f"SFTP connection test initiated: {config.get('host')}:{config.get('port')} with user {config.get('username')}")
            
            if SftpClient is None:
                logger.warning("SFTP client is not available")
                return jsonify({'success': False, 'message': 'SFTP client is not available'})
            
            client = SftpClient(
                host=config.get('host'),
                port=int(config.get('port', 22)),
                username=config.get('username'),
                password=config.get('password'),
                private_key=config.get('private_key'),
                private_key_passphrase=config.get('private_key_passphrase'),
                disable_host_key_checking=config.get('disable_host_key_checking', False)
            )
            
            success, message = client.test_connection()
            result = {'success': success, 'message': message}
            
        elif credential.credential_type == 'mssql':
            logger.debug(f"MSSQL connection test initiated: {config.get('server')}:{config.get('port')} with user {config.get('username')}")
            
            if MssqlClient is None:
                logger.warning("MSSQL client is not available")
                return jsonify({'success': False, 'message': 'MSSQL client is not available'})
            
            client = MssqlClient(
                server=config.get('server'),
                database=config.get('database'),
                username=config.get('username'),
                password=config.get('password'),
                port=int(config.get('port', 1433)),
                encrypt=config.get('encrypt', 'yes'),
                trust_server_certificate=config.get('trust_server_certificate', False)
            )
            
            success, message = client.test_connection()
            result = {'success': success, 'message': message}
            
        else:
            logger.warning(f"Testing not implemented for {credential.credential_type} credentials")
            result = {'success': False, 'message': f'Testing not implemented for {credential.credential_type} credentials'}
    
    except Exception as e:
        logger.error(f"Error testing credential {credential_id}: {str(e)}", exc_info=True)
        result = {'success': False, 'message': f'Error testing credential: {str(e)}'}
    
    logger.info(f"Credential test result: {result['success']}")
    return jsonify(result)

@credentials_bp.route('/<int:credential_id>/check_usage')
@login_required
def check_usage(credential_id):
    credential = Credential.query.get_or_404(credential_id)
    
    # Check ownership
    if credential.user_id != current_user.id:
        return jsonify({'success': False, 'message': 'You do not have permission to access this credential'})
    
    # Check if any jobs are using this credential
    jobs_using_credential = Job.query.filter(
        (Job.source_credential_id == credential.id) | 
        (Job.destination_credential_id == credential.id)
    ).all()
    
    if jobs_using_credential:
        job_names = ', '.join([job.name for job in jobs_using_credential])
        return jsonify({
            'used': True, 
            'jobs': [{'id': job.id, 'name': job.name} for job in jobs_using_credential],
            'message': f'Credential is being used by the following jobs: {job_names}'
        })
    
    return jsonify({'used': False, 'jobs': [], 'message': 'Credential is not used by any jobs'})
