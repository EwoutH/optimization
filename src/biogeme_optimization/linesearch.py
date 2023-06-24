"""File linesearch.py

:author: Michel Bierlaire
:date: Thu Jun 22 15:12:21 2023

Functions for line search algorithms
"""
import logging
import numpy as np
from biogeme_optimization.exceptions import OptimizationError
from biogeme_optimization.function import relative_gradient
from biogeme_optimization.algebra import schnabel_eskow_direction

logger = logging.getLogger(__name__)


def linesearch(
    fct, iterate, descent_direction, alpha0=1.0, beta1=1.0e-4, beta2=0.99, lbd=2.0
):
    """
    Calculate a step along a direction that satisfies both Wolfe conditions

    :param fct: object to calculate the objective function and its derivatives.
    :type fct: function_to_minimize

    :param iterate: current iterate.
    :type iterate: numpy.array

    :param descent_direction: descent direction.
    :type descent_direction: numpy.array

    :param alpha0: first step to test.
    :type alpha0: float

    :param beta1: parameter of the first Wolfe condition.
    :type beta1: float

    :param beta2: parameter of the second Wolfe condition.
    :type beta2: float

    :param lbd: expansion factor for a short step.
    :type lbd: float

    :return: a step verifing both Wolfe conditions
    :rtype: float

    :raises OptimizationError: if ``lbd`` :math:`\\leq` 1
    :raises OptimizationError: if ``alpha0`` :math:`\\leq` 0
    :raises OptimizationError: if ``beta1`` :math:`\\geq` beta2
    :raises OptimizationError: if ``descent_direction`` is not a descent
                                             direction

    """
    MAX_ITERATIONS = 1000

    if lbd <= 1:
        raise OptimizationError(f'lambda is {lbd} and must be > 1')
    if alpha0 <= 0:
        raise OptimizationError(f'alpha0 is {alpha0} and must be > 0')
    if beta1 >= beta2:
        error_msg = (
            f'Incompatible Wolfe cond. parameters: '
            f'beta1= {beta1} is greater than '
            f'beta2={beta2}'
        )
        raise OptimizationError(error_msg)

    fct.set_variables(iterate)
    function, gradient = fct.f_g()

    nbr_function_evaluations = 1
    deriv = np.inner(gradient, descent_direction)

    if deriv >= 0:
        raise OptimizationError(
            f'descent_direction is not a descent direction: {deriv} >= 0'
        )

    alpha = alpha0
    alphal = 0
    alphar = np.inf
    for _ in range(MAX_ITERATIONS):
        candidate = iterate + alpha * descent_direction
        fct.set_variables(candidate)
        value_candidate, gradient_candidate = fct.f_g()
        nbr_function_evaluations += 1
        # First Wolfe condition violated?
        if value_candidate > function + alpha * beta1 * deriv:
            alphar = alpha
            alpha = (alphal + alphar) / 2.0
        elif np.inner(gradient_candidate, descent_direction) < beta2 * deriv:
            alphal = alpha
            if alphar == np.inf:
                alpha = lbd * alpha
            else:
                alpha = (alphal + alphar) / 2.0
        else:
            break
    else:
        raise OptimizationError(
            f'Line search algorithm could not find a step verifying both Wolfe '
            f'conditions after {MAX_ITERATIONS} iterations.'
        )
    return alpha, nbr_function_evaluations


def newton_linesearch(
    fct, starting_point, eps=np.finfo(np.float64).eps ** 0.3333, maxiter=100
):
    """
    Newton method with inexact line search (Wolfe conditions)

    :param fct: object to calculate the objective function and its derivatives.
    :type fct: optimization.functionToMinimize

    :param starting_point: starting point
    :type starting_point: numpy.array

    :param eps: the algorithm stops when this precision is reached.
                 Default: :math:`\\varepsilon^{\\frac{1}{3}}`
    :type eps: float

    :param maxiter: the algorithm stops if this number of iterations
                    is reached. Defaut: 100
    :type maxiter: int

    :return: x, messages

        - x is the solution generated by the algorithm,
        - messages is a dictionary describing information about the lagorithm

    :rtype: numpay.array, dict(str:object)

    """

    xk = starting_point
    fct.set_variables(xk)
    f, g, h = fct.f_g_h()
    nfev = 1
    ngev = 1
    nhev = 1
    typx = np.ones_like(xk)
    typf = max(np.abs(f), 1.0)
    relgrad = relative_gradient(xk, f, g, typx, typf)
    if relgrad <= eps:
        message = f'Relative gradient = {relgrad:.3g} <= {eps:.2g}'
        messages = {
            'Algorithm': 'Unconstrained Newton with line search',
            'Relative gradient': relgrad,
            'Number of iterations': 0,
            'Number of function evaluations': nfev,
            'Number of gradient evaluations': ngev,
            'Number of hessian evaluations': nhev,
            'Cause of termination': message,
        }
        return xk, messages

    k = 0
    cont = True
    while cont:
        direction = schnabel_eskow_direction(g, h)
        alpha, nfls = linesearch(fct, xk, direction)
        nfev += nfls
        ngev += nfls
        xk += alpha * direction
        fct.set_variables(xk)
        f, g, h = fct.f_g_h()
        nfev += 1
        ngev += 1
        nhev += 1
        k += 1
        typf = max(np.abs(f), 1.0)
        relgrad = relative_gradient(xk, f, g, typx, typf)
        if relgrad <= eps:
            message = f'Relative gradient = {relgrad:.2g} <= {eps:.2g}'
            cont = False
        if k == maxiter:
            message = f'Maximum number of iterations reached: {maxiter}'
            cont = False
        logger.debug(f'{k} f={f:10.7g} relgrad={relgrad:6.2g}' f' alpha={alpha:6.2g}')

    messages = {
        'Algorithm': 'Unconstrained Newton with line search',
        'Relative gradient': relgrad,
        'Number of iterations': k,
        'Number of function evaluations': nfev,
        'Number of gradient evaluations': ngev,
        'Number of hessian evaluations': nhev,
        'Cause of termination': message,
    }

    return xk, messages
