from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app import models, oauth2
from app.contactModel import ContactTicket
public = APIRouter(
    prefix="/api/v2/contactus",
    tags=["Contactus"]
)

@public.get("/", response_model=List[ContactTicket])
def get_contact_tickets(db: Session = Depends(get_db)):
    return db.query(ContactTicket).all()


@public.post("/", response_model=ContactTicket)
def create_contact_ticket(ticket: ContactTicketBase, db: Session = Depends(get_db)):
    new_ticket = ContactTicket(**ticket.dict())
    db.add(new_ticket)
    db.commit()
    db.refresh(new_ticket)
    return new_ticket
