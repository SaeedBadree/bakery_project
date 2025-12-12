from sqlalchemy import Column, Integer, String, Numeric, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Ingredient(Base):
    __tablename__ = "ingredients"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, unique=True)
    unit = Column(String(20), nullable=False)  # g, kg, ml, unit
    cost_per_unit = Column(Numeric(10, 4), nullable=False)
    on_hand = Column(Numeric(10, 2), default=0)
    reorder_point = Column(Numeric(10, 2), default=0)
    
    recipe_lines = relationship("RecipeLine", back_populates="ingredient")
    batch_consumption = relationship("BatchConsumption", back_populates="ingredient")


class Recipe(Base):
    __tablename__ = "recipes"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, unique=True)
    yield_qty = Column(Numeric(10, 2), nullable=False)
    yield_unit = Column(String(20), nullable=False)
    notes = Column(String(1000))
    
    recipe_lines = relationship("RecipeLine", back_populates="recipe", cascade="all, delete-orphan")
    batches = relationship("Batch", back_populates="recipe")


class RecipeLine(Base):
    __tablename__ = "recipe_lines"
    
    id = Column(Integer, primary_key=True, index=True)
    recipe_id = Column(Integer, ForeignKey("recipes.id"), nullable=False)
    ingredient_id = Column(Integer, ForeignKey("ingredients.id"), nullable=False)
    qty = Column(Numeric(10, 2), nullable=False)
    
    recipe = relationship("Recipe", back_populates="recipe_lines")
    ingredient = relationship("Ingredient", back_populates="recipe_lines")


class Batch(Base):
    __tablename__ = "batches"
    
    id = Column(Integer, primary_key=True, index=True)
    recipe_id = Column(Integer, ForeignKey("recipes.id"), nullable=False)
    qty_produced = Column(Numeric(10, 2), nullable=False)
    produced_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    wastage = Column(Numeric(10, 2), default=0)
    notes = Column(String(500))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    recipe = relationship("Recipe", back_populates="batches")
    user = relationship("User", back_populates="batches")
    consumption = relationship("BatchConsumption", back_populates="batch", cascade="all, delete-orphan")


class BatchConsumption(Base):
    __tablename__ = "batch_consumption"
    
    id = Column(Integer, primary_key=True, index=True)
    batch_id = Column(Integer, ForeignKey("batches.id"), nullable=False)
    ingredient_id = Column(Integer, ForeignKey("ingredients.id"), nullable=False)
    qty_used = Column(Numeric(10, 2), nullable=False)
    
    batch = relationship("Batch", back_populates="consumption")
    ingredient = relationship("Ingredient", back_populates="batch_consumption")

