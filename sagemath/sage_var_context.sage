# -*- coding: utf-8 -*-

class SageVarContext:
    """
    A context manager for representing SageMath Expressions as LaTeX
    with their values substituted a step at a time
    """
    ROUNDING_NDIGITS = 15
    
    def __init__(self):
        # SageMath variable -> (latex_name, value)
        self._vars = dict()
    
    def __enter__(self):
        return self
    
    @staticmethod
    def _safe_name(unsafe_name):
        safe_name = unsafe_name
        safe_name = safe_name.replace(' ', '')
        safe_name = safe_name.replace('*', 'TIMES')
        safe_name = safe_name.replace('-', 'MINUS')
        safe_name = safe_name.replace('+', 'PLUS')
        safe_name = safe_name.replace('/', 'FSLASH')
        safe_name = safe_name.replace('\\', 'BSLASH')
        safe_name = safe_name.replace('$', 'DOLLAR')
        safe_name = safe_name.replace('@', 'AT')
        safe_name = safe_name.replace('!', 'EXCLAM')
        safe_name = safe_name.replace('~', 'TILDE')
        safe_name = safe_name.replace('`', 'BTICK')
        safe_name = safe_name.replace('^', 'EXPON')
        safe_name = safe_name.replace('#', 'POUND')
        safe_name = safe_name.replace('=', 'EQL')
        safe_name = safe_name.replace('[', 'OBCK')
        safe_name = safe_name.replace(']', 'CBCK')
        safe_name = safe_name.replace('{', 'OBCE')
        safe_name = safe_name.replace('}', 'CBCE')
        safe_name = safe_name.replace('(', 'OP')
        safe_name = safe_name.replace(')', 'CP')
        return safe_name
    
    @staticmethod
    def _is_float(value):
        try:
            float(value)
        except TypeError, ValueError:
            return False
        return True
    
    @classmethod
    def _maybe_round(cls, value):
        # Hack to round number if it's too long
        assert cls._is_float(value)
        value_str = str(value)
        if '.' not in value_str:
            return value_str
        value_str = str(float(value))
        if len(value_str.split('.')[1]) > 10:
            value_str = str(value.n(cls.ROUNDING_NDIGITS))
        return value_str
    
    @classmethod
    def _sage_str(cls, value):
        if cls._is_float(value):
            return cls._maybe_round(value)
        return str(value)
    
    def latex_var(self, latex_name, sage_name=None, value=None):
        """Create a new SageMath variable with an optional value"""
        if sage_name is None:
            new_var = var(self._safe_name(latex_name), latex_name=latex_name)
        else:
            new_var = var(sage_name, latex_name=latex_name)
        self._vars[new_var] = latex_name, value
        return new_var
    
    def substitute_values(self, expression):
        """Substitute values into the sage Expression and return a new LatexExpr"""
        # We treat sage Expression as a string so we do variable replacements manually
        latex_expr = latex(expression)
        for sage_var in expression.variables():
            latex_name, value = self._vars.get(sage_var, (None, None))
            if value is not None:
                src_str = '{' + latex_name + '}'
                dst_str = '{(' + self._sage_str(value) + ')}'
                latex_expr = latex_expr.replace(src_str, dst_str)
        return LatexExpr(latex_expr)
    
    def evaluate_values(self, expression):
        """Evaluate the expression with the values given and return the resulting expression"""
        new_expr = expression
        for sage_var, (_, value) in self._vars.items():
            if value is None:
                continue
            new_expr = new_expr.substitute(sage_var==value)
        return new_expr
    
    def generate_rhs_work(self, expression):
        latex_final = latex(expression)
        latex_final += LatexExpr('=')
        latex_final += self.substitute_values(expression.rhs())
        latex_final += LatexExpr(r'\approx')
        try:
            latex_final += self.evaluate_values(expression.rhs()).n(self.ROUNDING_NDIGITS)
        except TypeError:
            latex_final += self.evaluate_values(expression.rhs())
        return latex_final
    
    def __exit__(self, type, value, traceback):
        reset(vars=self._vars)

sage.misc.reset.EXCLUDE.add('SageVarContext')
