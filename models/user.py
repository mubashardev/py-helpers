from sqlmodel import Field
from my_sqlmodel import MySQLModel


class UserBase (MySQLModel):
    name: str = Field()
    email: str = Field()
    password: str = Field()

class User (UserBase, table = True):
    id: int = Field(primary_key=True)