from app import create_app, db
from app.models.user import User
from app.models.job import Job
from app.models.credential import Credential
from app.models.log import Log

app = create_app()

@app.shell_context_processor
def make_shell_context():
    return {
        'db': db, 
        'User': User, 
        'Job': Job, 
        'Credential': Credential,
        'Log': Log
    }

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
