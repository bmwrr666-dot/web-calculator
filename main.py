import ast
import math
import operator
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

app = FastAPI()

# Allowed mathematical functions
SAFE_FUNCTIONS = {
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "sqrt": math.sqrt,
    "log": math.log,
    "pi": math.pi,
    "e": math.e,
}

# Allowed binary operators
SUPPORTED_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
}


def safe_eval(node):
  """Recursively evaluates the AST safely for math and functions."""
  if isinstance(node, ast.Constant):
    if isinstance(node.value, (int, float)):
      return node.value
    raise ValueError(f"Unsupported constant: {type(node.value)}")

  elif isinstance(node, ast.BinOp):
    op_type = type(node.op)
    if op_type in SUPPORTED_OPERATORS:
      return SUPPORTED_OPERATORS[op_type](
          safe_eval(node.left), safe_eval(node.right)
      )
    raise ValueError("Unsupported operator")

  elif isinstance(node, ast.UnaryOp):
    if isinstance(node.op, ast.UAdd):
      return safe_eval(node.operand)
    elif isinstance(node.op, ast.USub):
      return -safe_eval(node.operand)
    raise ValueError("Unsupported unary operator")

  elif isinstance(node, ast.Call):  # Handles functions like sqrt(16) or sin(90)
    if isinstance(node.func, ast.Name) and node.func.id in SAFE_FUNCTIONS:
      func = SAFE_FUNCTIONS[node.func.id]
      # Evaluate all arguments passed to the function
      args = [safe_eval(arg) for arg in node.args]
      if callable(func):
        return func(*args)
      return func  # For constants like pi or e
    raise ValueError(f"Unsupported function call")

  elif isinstance(node, ast.Name):  # Handles constants like pi, e
    if node.id in SAFE_FUNCTIONS:
      val = SAFE_FUNCTIONS[node.id]
      if not callable(val):
        return val
    raise ValueError(f"Unknown variable: {node.id}")

  raise TypeError(f"Invalid expression syntax")


# Pydantic model for incoming JSON request
class CalculationRequest(BaseModel):
  expression: str


@app.post("/calculate")
def calculate(req: CalculationRequest):
  expr = req.expression.strip().replace("^", "**")
  if not expr:
    raise HTTPException(status_code=400, detail="Empty expression")
  try:
    tree = ast.parse(expr, mode="eval")
    result = safe_eval(tree.body)
    return {"result": result}
  except ZeroDivisionError:
    return {"result": "Error: Division by zero"}
  except Exception as e:
    return {"result": f"Error: Invalid syntax"}


@app.get("/", response_class=HTMLResponse)
def serve_homepage():
  with open("templates/index.html", "r", encoding="utf-8") as f:
    return f.read()