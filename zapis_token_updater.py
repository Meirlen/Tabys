import time
from app import models, schemas as schemas
from app.database import get_db_singleton
from app.schemas import *
from app.zapis_kz.zapis_api import get_masters
def token_checker():
    db = get_db_singleton()
    accesss_token = db.query(models.Credentials).filter(models.Credentials.token_type == "access_token").first().value
    refresh_token = db.query(models.Credentials).filter(models.Credentials.token_type == "refresh_token").first().value

    if accesss_token:
        print(f"accesss_token:  {accesss_token}")
        print(f"refresh_token:  {refresh_token}")

        get_masters(2138)
    else:
        print("Ошибка аутентификации Zapis KZ")

def init_token(auth_token, refresh_token):
    db = get_db_singleton()
    cred = db.query(models.Credentials).filter(models.Credentials.token_type == "access_token").first()

    if cred:

        db = get_db_singleton()
        cred = db.query(models.Credentials).filter(models.Credentials.token_type == "access_token")
        cred.update({"value": str(auth_token)}, synchronize_session=False)
        db.commit()
        db.close()

        cred = db.query(models.Credentials).filter(models.Credentials.token_type == "refresh_token")
        cred.update({"value": str(refresh_token)}, synchronize_session=False)
        db.commit()
        db.close()
    else:
        db_credentials = models.Credentials(
            service_name= "zapis",
            token_type="access_token",
            value=auth_token,
        )

        db.add(db_credentials)
        db.commit()
        db.refresh(db_credentials)

        db_credentials = models.Credentials(
            service_name="zapis",
            token_type="refresh_token",
            value=refresh_token,
        )

        db.add(db_credentials)
        db.commit()
        db.refresh(db_credentials)


def update_token_by_timer():
    while True :

        try:
            token_checker()
            print("token_checker")
        except:
            print("Error")

        time.sleep(30)

update_token_by_timer()
# access_token = "eyJraWQiOiIwc2RPYVhGTmtyb3FCYXdqUElqNm03cm5TYmd0S0Y5Q3VLbEN0ZFBkZjAwIiwiYWxnIjoiUlMyNTYifQ.eyJzdWIiOiI4MTAxODQiLCJzY29wZSI6IlBBUlRORVIiLCJpc3MiOiJodHRwczpcL1wvYXV0aDIuemFwaXMubWUiLCJmaXJtcyI6W3sicGFydG5lclN0YXR1cyI6IkRJUkVDVE9SIiwicm9sZUlkIjo0NzEyNywiaWQiOjExMzkyLCJpc1JlbWluZDM2NUF2YWlsYWJsZSI6dHJ1ZSwicGVybWlzc2lvbklkcyI6bnVsbH1dLCJleHAiOjE3MzMyMDc5NjMsImlhdCI6MTczMzIwNDM2M30.FVPkuPame2IS50rpxRAPHiN0UwgCfeMHYsGGH4DA9Y2_9glTlx9NGyrZM03htq_ZuwIwiNwj6uyBKnj5j9V62TWKmGKKWbGx9SyZ4LZT2c-07tkdLMeg2brFm4RDwV8lhsQ03EDBDnCKAAaTCYVbn8JDSMui52KPdsnH98_wRKMMARvzTb2F0YN4s6qe36go7kr-6wLUFpS2-l81buiiEHzKayqVjj-uLvscjWrA4L2k9YmzTml1h6CuWvfk9I0hmAPRN6KN951qDWEigc1fT0u1dXKxLMLcUjOhHopfpvFLfl-gFGxBp-dIuwb6JOHIq7HQMHplmKZCeWUTxyonuQ"
# refresh_token = "eyJraWQiOiIwc2RPYVhGTmtyb3FCYXdqUElqNm03cm5TYmd0S0Y5Q3VLbEN0ZFBkZjAwIiwiYWxnIjoiUlMyNTYifQ.eyJpc3MiOiJodHRwczpcL1wvYXV0aDIuemFwaXMubWUiLCJzdWIiOiI4MTAxODQiLCJleHAiOjE3NjQ3NDAzNjMsImlhdCI6MTczMzIwNDM2M30.bhIVvgvSBbUaKs6bP3-rb36azlnN0-Qxt517uRAf_20NHsxembIlMzbDOIZOo68Dskez-m6XKtDqAw042cveTsEYpvP2fgYHTEUpBl-tNrG6qu1pp07uvI21DSvTpxNlFEAeR-BKGR315phwUZOPaBkZGgt3qfzunpsi8BEhFNEBThK91jyAR9gWI6UrTw3cgumgmq5kx5neT9X7LFECOowflo7c-Jpg5eY2JTEhu1ZSHLrBQsostnuWnMF5JeIJXP44eD2geayVky6A7oeVIKOV9Us0Bhihra6DCivL-uemFgzjXhfi2M0y_OxRly0kULBa9z_6j8GwToK8-zFDWg"
# init_token(access_token, refresh_token)