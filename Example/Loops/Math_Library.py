# Focused math library workload; ordinary Python inputs include supported and retained cases.
import math
import cmath
import numpy as np
from math import sin as Wave
Literal_Finite = 1.25
Literal_Zero = -0.0
Literal_Infinite = 1e10000
Literal_Tuple = (1.25, -0.0)

def Real_acos(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = math.acos(Source[Index])
    return Output

def Real_acosh(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = math.acosh(Source[Index])
    return Output

def Real_asin(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = math.asin(Source[Index])
    return Output

def Real_asinh(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = math.asinh(Source[Index])
    return Output

def Real_atan(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = math.atan(Source[Index])
    return Output

def Real_atan2(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = math.atan2(Source[Index], 2.0)
    return Output

def Real_atanh(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = math.atanh(Source[Index])
    return Output

def Real_cbrt(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = math.cbrt(Source[Index])
    return Output

def Real_ceil(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = math.ceil(Source[Index])
    return Output

def Real_comb(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = math.comb(Source[Index], 1)
    return Output

def Real_copysign(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = math.copysign(Source[Index], 2.0)
    return Output

def Real_cos(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = math.cos(Source[Index])
    return Output

def Real_cosh(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = math.cosh(Source[Index])
    return Output

def Real_degrees(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = math.degrees(Source[Index])
    return Output

def Real_dist(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = math.dist((Source[Index], 1.0), (0.0, 2.0))
    return Output

def Real_erf(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = math.erf(Source[Index])
    return Output

def Real_erfc(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = math.erfc(Source[Index])
    return Output

def Real_exp(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = math.exp(Source[Index])
    return Output

def Real_exp2(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = math.exp2(Source[Index])
    return Output

def Real_expm1(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = math.expm1(Source[Index])
    return Output

def Real_fabs(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = math.fabs(Source[Index])
    return Output

def Real_factorial(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = math.factorial(Source[Index])
    return Output

def Real_floor(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = math.floor(Source[Index])
    return Output

def Real_fmod(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = math.fmod(Source[Index], 2.0)
    return Output

def Real_frexp(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = math.frexp(Source[Index])[0]
    return Output

def Real_fsum(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = math.fsum([Source[Index], 1.0, -1.0])
    return Output

def Real_gamma(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = math.gamma(Source[Index])
    return Output

def Real_gcd(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = math.gcd(Source[Index], 6)
    return Output

def Real_hypot(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = math.hypot(Source[Index], 1.0, 2.0)
    return Output

def Real_isclose(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = math.isclose(Source[Index], Source[Index], abs_tol=0.0)
    return Output

def Real_isfinite(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = math.isfinite(Source[Index])
    return Output

def Real_isinf(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = math.isinf(Source[Index])
    return Output

def Real_isnan(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = math.isnan(Source[Index])
    return Output

def Real_isqrt(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = math.isqrt(Source[Index])
    return Output

def Real_lcm(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = math.lcm(Source[Index], 6)
    return Output

def Real_ldexp(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = math.ldexp(0.5, Source[Index])
    return Output

def Real_lgamma(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = math.lgamma(Source[Index])
    return Output

def Real_log(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = math.log(Source[Index])
    return Output

def Real_log10(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = math.log10(Source[Index])
    return Output

def Real_log1p(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = math.log1p(Source[Index])
    return Output

def Real_log2(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = math.log2(Source[Index])
    return Output

def Real_modf(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = math.modf(Source[Index])[0]
    return Output

def Real_nextafter(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = math.nextafter(Source[Index], math.inf)
    return Output

def Real_perm(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = math.perm(Source[Index], 1)
    return Output

def Real_pow(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = math.pow(Source[Index], 2.0)
    return Output

def Real_prod(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = math.prod([Source[Index], 2])
    return Output

def Real_radians(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = math.radians(Source[Index])
    return Output

def Real_remainder(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = math.remainder(Source[Index], 2.0)
    return Output

def Real_sin(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = math.sin(Source[Index])
    return Output

def Real_sinh(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = math.sinh(Source[Index])
    return Output

def Real_sqrt(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = math.sqrt(Source[Index])
    return Output

def Real_tan(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = math.tan(Source[Index])
    return Output

def Real_tanh(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = math.tanh(Source[Index])
    return Output

def Real_trunc(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = math.trunc(Source[Index])
    return Output

def Real_ulp(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = math.ulp(Source[Index])
    return Output

def Real_fma(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = math.fma(Source[Index], 2.0, 1.0)
    return Output

def Real_sumprod(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = math.sumprod([Source[Index], 1.0], [2.0, 3.0])
    return Output

def Complex_acos(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = cmath.acos(Source[Index])
    return Output

def Complex_acosh(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = cmath.acosh(Source[Index])
    return Output

def Complex_asin(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = cmath.asin(Source[Index])
    return Output

def Complex_asinh(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = cmath.asinh(Source[Index])
    return Output

def Complex_atan(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = cmath.atan(Source[Index])
    return Output

def Complex_atanh(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = cmath.atanh(Source[Index])
    return Output

def Complex_cos(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = cmath.cos(Source[Index])
    return Output

def Complex_cosh(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = cmath.cosh(Source[Index])
    return Output

def Complex_exp(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = cmath.exp(Source[Index])
    return Output

def Complex_isclose(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = cmath.isclose(Source[Index], Source[Index])
    return Output

def Complex_isfinite(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = cmath.isfinite(Source[Index])
    return Output

def Complex_isinf(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = cmath.isinf(Source[Index])
    return Output

def Complex_isnan(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = cmath.isnan(Source[Index])
    return Output

def Complex_log(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = cmath.log(Source[Index])
    return Output

def Complex_log10(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = cmath.log10(Source[Index])
    return Output

def Complex_phase(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = cmath.phase(Source[Index])
    return Output

def Complex_polar(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = cmath.polar(Source[Index])[0]
    return Output

def Complex_rect(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = cmath.rect(Source[Index], 0.5)
    return Output

def Complex_sin(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = cmath.sin(Source[Index])
    return Output

def Complex_sinh(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = cmath.sinh(Source[Index])
    return Output

def Complex_sqrt(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = cmath.sqrt(Source[Index])
    return Output

def Complex_tan(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = cmath.tan(Source[Index])
    return Output

def Complex_tanh(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = cmath.tanh(Source[Index])
    return Output

def Numpy_add(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = np.add(Source[Index], 2.0)
    return Output

def Numpy_subtract(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = np.subtract(Source[Index], 2.0)
    return Output

def Numpy_multiply(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = np.multiply(Source[Index], 2.0)
    return Output

def Numpy_divide(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = np.divide(Source[Index], 2.0)
    return Output

def Numpy_true_divide(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = np.true_divide(Source[Index], 2.0)
    return Output

def Numpy_floor_divide(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = np.floor_divide(Source[Index], 2.0)
    return Output

def Numpy_power(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = np.power(Source[Index], 2.0)
    return Output

def Numpy_float_power(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = np.float_power(Source[Index], 2.0)
    return Output

def Numpy_square(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = np.square(Source[Index])
    return Output

def Numpy_reciprocal(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = np.reciprocal(Source[Index])
    return Output

def Numpy_positive(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = np.positive(Source[Index])
    return Output

def Numpy_negative(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = np.negative(Source[Index])
    return Output

def Numpy_absolute(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = np.absolute(Source[Index])
    return Output

def Numpy_fabs(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = np.fabs(Source[Index])
    return Output

def Numpy_sign(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = np.sign(Source[Index])
    return Output

def Numpy_sqrt(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = np.sqrt(Source[Index])
    return Output

def Numpy_cbrt(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = np.cbrt(Source[Index])
    return Output

def Numpy_exp(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = np.exp(Source[Index])
    return Output

def Numpy_exp2(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = np.exp2(Source[Index])
    return Output

def Numpy_expm1(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = np.expm1(Source[Index])
    return Output

def Numpy_log(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = np.log(Source[Index])
    return Output

def Numpy_log2(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = np.log2(Source[Index])
    return Output

def Numpy_log10(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = np.log10(Source[Index])
    return Output

def Numpy_log1p(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = np.log1p(Source[Index])
    return Output

def Numpy_logaddexp(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = np.logaddexp(Source[Index], 2.0)
    return Output

def Numpy_logaddexp2(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = np.logaddexp2(Source[Index], 2.0)
    return Output

def Numpy_sin(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = np.sin(Source[Index])
    return Output

def Numpy_cos(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = np.cos(Source[Index])
    return Output

def Numpy_tan(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = np.tan(Source[Index])
    return Output

def Numpy_arcsin(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = np.arcsin(Source[Index])
    return Output

def Numpy_arccos(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = np.arccos(Source[Index])
    return Output

def Numpy_arctan(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = np.arctan(Source[Index])
    return Output

def Numpy_arctan2(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = np.arctan2(Source[Index], 2.0)
    return Output

def Numpy_hypot(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = np.hypot(Source[Index], 2.0)
    return Output

def Numpy_degrees(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = np.degrees(Source[Index])
    return Output

def Numpy_radians(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = np.radians(Source[Index])
    return Output

def Numpy_deg2rad(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = np.deg2rad(Source[Index])
    return Output

def Numpy_rad2deg(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = np.rad2deg(Source[Index])
    return Output

def Numpy_unwrap(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = np.unwrap([Source[Index], 1.0, 2.0])[0]
    return Output

def Numpy_sinh(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = np.sinh(Source[Index])
    return Output

def Numpy_cosh(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = np.cosh(Source[Index])
    return Output

def Numpy_tanh(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = np.tanh(Source[Index])
    return Output

def Numpy_arcsinh(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = np.arcsinh(Source[Index])
    return Output

def Numpy_arccosh(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = np.arccosh(Source[Index])
    return Output

def Numpy_arctanh(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = np.arctanh(Source[Index])
    return Output

def Numpy_sinc(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = np.sinc(Source[Index])
    return Output

def Numpy_i0(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = np.i0(Source[Index])
    return Output

def Numpy_round(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = np.round(Source[Index])
    return Output

def Numpy_around(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = np.around(Source[Index])
    return Output

def Numpy_rint(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = np.rint(Source[Index])
    return Output

def Numpy_fix(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = np.fix(Source[Index])
    return Output

def Numpy_floor(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = np.floor(Source[Index])
    return Output

def Numpy_ceil(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = np.ceil(Source[Index])
    return Output

def Numpy_trunc(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = np.trunc(Source[Index])
    return Output

def Numpy_fmod(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = np.fmod(Source[Index], 2.0)
    return Output

def Numpy_mod(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = np.mod(Source[Index], 2.0)
    return Output

def Numpy_remainder(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = np.remainder(Source[Index], 2.0)
    return Output

def Numpy_modf(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = np.modf(Source[Index])[0]
    return Output

def Numpy_divmod(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = np.divmod(Source[Index], 2.0)[0]
    return Output

def Numpy_copysign(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = np.copysign(Source[Index], 2.0)
    return Output

def Numpy_signbit(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = np.signbit(Source[Index])
    return Output

def Numpy_frexp(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = np.frexp(Source[Index])[0]
    return Output

def Numpy_ldexp(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = np.ldexp(0.5, Source[Index])
    return Output

def Numpy_nextafter(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = np.nextafter(Source[Index], 2.0)
    return Output

def Numpy_spacing(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = np.spacing(Source[Index])
    return Output

def Numpy_isfinite(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = np.isfinite(Source[Index])
    return Output

def Numpy_isinf(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = np.isinf(Source[Index])
    return Output

def Numpy_isnan(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = np.isnan(Source[Index])
    return Output

def Numpy_isclose(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = np.isclose(Source[Index], 2.0)
    return Output

def Numpy_allclose(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = np.allclose(Source[Index], 2.0)
    return Output

def Numpy_minimum(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = np.minimum(Source[Index], 2.0)
    return Output

def Numpy_maximum(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = np.maximum(Source[Index], 2.0)
    return Output

def Numpy_fmin(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = np.fmin(Source[Index], 2.0)
    return Output

def Numpy_fmax(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = np.fmax(Source[Index], 2.0)
    return Output

def Numpy_clip(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = np.clip(Source[Index], 0.0, 1.0)
    return Output

def Numpy_gcd(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = np.gcd(Source[Index], 6)
    return Output

def Numpy_lcm(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = np.lcm(Source[Index], 6)
    return Output

def Numpy_sum(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = np.sum([Source[Index], 1.0, 2.0])
    return Output

def Numpy_prod(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = np.prod([Source[Index], 1.0, 2.0])
    return Output

def Numpy_min(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = np.min([Source[Index], 1.0, 2.0])
    return Output

def Numpy_max(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = np.max([Source[Index], 1.0, 2.0])
    return Output

def Numpy_mean(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = np.mean([Source[Index], 1.0, 2.0])
    return Output

def Numpy_var(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = np.var([Source[Index], 1.0, 2.0])
    return Output

def Numpy_std(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = np.std([Source[Index], 1.0, 2.0])
    return Output

def Numpy_nansum(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = np.nansum([Source[Index], 1.0, 2.0])
    return Output

def Numpy_nanprod(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = np.nanprod([Source[Index], 1.0, 2.0])
    return Output

def Numpy_nanmin(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = np.nanmin([Source[Index], 1.0, 2.0])
    return Output

def Numpy_nanmax(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = np.nanmax([Source[Index], 1.0, 2.0])
    return Output

def Numpy_nanmean(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = np.nanmean([Source[Index], 1.0, 2.0])
    return Output

def Numpy_nanvar(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = np.nanvar([Source[Index], 1.0, 2.0])
    return Output

def Numpy_nanstd(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = np.nanstd([Source[Index], 1.0, 2.0])
    return Output

def Numpy_cumsum(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = np.cumsum([Source[Index], 1.0, 2.0])[0]
    return Output

def Numpy_cumprod(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = np.cumprod([Source[Index], 1.0, 2.0])[0]
    return Output

def Numpy_nancumsum(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = np.nancumsum([Source[Index], 1.0, 2.0])[0]
    return Output

def Numpy_nancumprod(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = np.nancumprod([Source[Index], 1.0, 2.0])[0]
    return Output

def Numpy_diff(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = np.diff([Source[Index], 1.0, 2.0])[0]
    return Output

def Numpy_gradient(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = np.gradient([Source[Index], 1.0, 2.0])[0]
    return Output

def Numpy_real(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = np.real(Source[Index])
    return Output

def Numpy_imag(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = np.imag(Source[Index])
    return Output

def Numpy_angle(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = np.angle(Source[Index])
    return Output

def Numpy_conj(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = np.conj(Source[Index])
    return Output

def Numpy_conjugate(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = np.conjugate(Source[Index])
    return Output

def Numpy_asin(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = np.asin(Source[Index])
    return Output

def Numpy_acos(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = np.acos(Source[Index])
    return Output

def Numpy_atan(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = np.atan(Source[Index])
    return Output

def Numpy_atan2(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = np.atan2(Source[Index], 2.0)
    return Output

def Numpy_asinh(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = np.asinh(Source[Index])
    return Output

def Numpy_acosh(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = np.acosh(Source[Index])
    return Output

def Numpy_atanh(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = np.atanh(Source[Index])
    return Output

def Numpy_pow(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = np.pow(Source[Index], 2.0)
    return Output

def Numpy_amin(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = np.amin([Source[Index], 1.0, 2.0])
    return Output

def Numpy_amax(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = np.amax([Source[Index], 1.0, 2.0])
    return Output

def Numpy_cumulative_sum(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = np.cumulative_sum([Source[Index], 1.0, 2.0])[0]
    return Output

def Numpy_cumulative_prod(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = np.cumulative_prod([Source[Index], 1.0, 2.0])[0]
    return Output

def Builtin_abs(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = abs(Source[Index])
    return Output

def Builtin_round(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = round(Source[Index], 2)
    return Output

def Builtin_pow(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = pow(Source[Index], 2)
    return Output

def Builtin_divmod(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = divmod(Source[Index], 2)[0]
    return Output

def Builtin_sum(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = sum([Source[Index], 1.0])
    return Output

def Builtin_min(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = min([Source[Index], 1.0])
    return Output

def Builtin_max(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = max([Source[Index], 1.0])
    return Output

def Builtin_int(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = int(Source[Index])
    return Output

def Builtin_float(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = float(Source[Index])
    return Output

def Builtin_complex(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = complex(Source[Index])
    return Output

def Builtin_bool(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = bool(Source[Index])
    return Output

def Composite(Source, Output):
    for Index in range(len(Output)):
        Value = math.sqrt(Source[Index])
        Value += Wave(Value)
        Output[Index] = math.exp(Value) + math.log(Source[Index], 2) + math.cos(math.pi)
    return Output

def Nested(Source, Output):
    for Row in range(Output.shape[0]):
        for Column in range(Output.shape[1]):
            if Source[Row, Column] < 0:
                continue
            Output[Row, Column] = math.sqrt(Source[Row, Column])
    return Output

def Float32_Intermediates(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = math.sin(Source[Index]) + math.cos(Source[Index])
    return Output

def Fraction(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = math.frexp(Source[Index])[1]
    return Output

def Literal_Identity(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = math.copysign(Source[Index], -0.0)
    return Output

def Infinite_Literal(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = math.copysign(Source[Index], 1e10000)
    return Output

def Collision(Baseline, Allow_Threads):
    for _Pyceler_Math_B in range(len(Allow_Threads)):
        Allow_Threads[_Pyceler_Math_B] = math.sqrt(Baseline[_Pyceler_Math_B])
    return Allow_Threads

def Identity_Finite(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = math.copysign(Source[Index], 1.25)
    return Output

def Identity_Zero(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = math.copysign(Source[Index], -0.0)
    return Output

def Identity_Infinite(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = math.copysign(Source[Index], 1e10000)
    return Output

def Identity_Tuple(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = math.prod((1.25, -0.0), start=Source[Index])
    return Output
