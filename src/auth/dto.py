# from pydantic import BaseModel
# from typing import List

# class User(BaseModel):
#     id: str
#     username: str
#     email: str
#     roles: List[str]


from pydantic import BaseModel



class UserPrincipal(BaseModel):
    email: str 
    roles: list[str] = []
    first_name: str | None = None
    last_name: str | None = None
    sub: str
