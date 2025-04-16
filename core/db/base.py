from sqlalchemy import func

from core.db.db import SessionLocal


class CRUDBase:
    def __init__(self, model):
        self.model = model
        self.session = SessionLocal()

    def get(self, id):
        return self.session.get(self.model, id)

    def get_all(self):
        return self.session.query(self.model).all()

    def filter(self, **kwargs):
        return self.session.query(self.model).filter_by(**kwargs).all()

    def group_by(self, group_by_name, **kwargs) -> dict:
        query = self.filter(**kwargs)
        ret_data = {}
        for q in query:
            if getattr(q, group_by_name) not in ret_data.keys():
                ret_data[getattr(q, group_by_name)] = []
            ret_data[getattr(q, group_by_name)].append(q.__dict__)

        return ret_data

    def add(self, **kwargs):
        obj = self.model(**kwargs)
        self.session.add(obj)
        self.session.commit()
        return obj

    def update(self, id, **kwargs):
        obj = self.get(id)
        if not obj:
            return None
        for key, value in kwargs.items():
            setattr(obj, key, value)
        self.session.commit()
        return obj

    def delete(self, id):
        obj = self.get(id)
        if obj:
            self.session.delete(obj)
            self.session.commit()
            return True
        return False

    def close(self):
        self.session.close()
