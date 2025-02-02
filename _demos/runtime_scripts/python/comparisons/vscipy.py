import math
from scipy.optimize import root_scalar  # type: ignore
import numpy as np
import functools


def quadratic_roots(a, b, c):
    sqrt_discriminant = math.sqrt(b**2 - 4 * a * c)
    root1 = (-b - sqrt_discriminant) / (2 * a)
    root2 = (-b + sqrt_discriminant) / (2 * a)
    return root1, root2


def ci_func(
    ci,
    lmr_z,
    par_z,
    gb_mol,
    je,
    cair,
    oair,
    rh_can,
    p,
    iv,
    c,
    c3flag=True,
    stomatalcond_mtd=1,
):
    # Constants
    forc_pbot = 121000.0
    medlynslope = 6.0
    medlynintercept = 10000.0
    vcmax_z = 62.5
    cp = 4.275
    kc = 40.49
    ko = 27840.0
    qe = 1.0
    tpu_z = 31.5
    kp_z = 1.0
    bbb = 100.0
    mbb = 9.0
    theta_cj = 0.98
    theta_ip = 0.95
    stomatalcond_mtd_medlyn2011 = 1
    stomatalcond_mtd_bb1987 = 2

    # C3 or C4 photosynthesis
    if c3flag:
        ac = vcmax_z * max(ci - cp, 0.0) / (ci + kc * (1.0 + oair / ko))
        aj = je * max(ci - cp, 0.0) / (4.0 * ci + 8.0 * cp)
        ap = 3.0 * tpu_z
    else:
        ac = vcmax_z
        aj = qe * par_z * 4.6
        ap = kp_z * max(ci, 0.0) / forc_pbot

    # Gross photosynthesis
    aquad = theta_cj
    bquad = -(ac + aj)
    cquad = ac * aj
    r1, r2 = quadratic_roots(aquad, bquad, cquad)
    ai = min(r1, r2)

    aquad = theta_ip
    bquad = -(ai + ap)
    cquad = ai * ap
    r1, r2 = quadratic_roots(aquad, bquad, cquad)
    ag = max(0.0, min(r1, r2))

    # Net photosynthesis
    an = ag - lmr_z
    if an < 0.0:
        fval = 0.0
        return fval, None, None

    # Quadratic gs_mol calculation
    cs = cair - 1.4 / gb_mol * an * forc_pbot
    if stomatalcond_mtd == stomatalcond_mtd_medlyn2011:
        term = 1.6 * an / (cs / forc_pbot * 1.0e06)
        aquad = 1.0
        bquad = -(
            2.0 * (medlynintercept * 1.0e-06 + term)
            + (medlynslope * term) ** 2 / (gb_mol * 1.0e-06 * rh_can)
        )
        cquad = (
            medlynintercept**2 * 1.0e-12
            + (
                2.0 * medlynintercept * 1.0e-06
                + term * (1.0 - medlynslope**2 / rh_can)
            )
            * term
        )
        r1, r2 = quadratic_roots(aquad, bquad, cquad)
        gs_mol = max(r1, r2) * 1.0e06
    elif stomatalcond_mtd == stomatalcond_mtd_bb1987:
        aquad = cs
        bquad = cs * (gb_mol - bbb) - mbb * an * forc_pbot
        cquad = -gb_mol * (cs * bbb + mbb * an * forc_pbot * rh_can)
        r1, r2 = quadratic_roots(aquad, bquad, cquad)
        gs_mol = max(r1, r2)
    else:
        gs_mol = 0.0

    # Derive new estimate for ci
    fval = ci - cair + an * forc_pbot * (1.4 / gb_mol + 1.6 / gs_mol)

    return fval, gs_mol, an


# Define a function to find the root of my_function
def root_func(lmr_z, par_z, gb_mol, je, cair, oair, rh_can, p, iv, c):
    partial = functools.partial(
        ci_func,
        lmr_z=lmr_z,
        par_z=par_z,
        gb_mol=gb_mol,
        je=je,
        cair=cair,
        oair=oair,
        rh_can=rh_can,
        p=p,
        iv=iv,
        c=c,
    )
    return lambda x: partial(x)[0]


def solve_ci(ci, f):
    # First find a negative value
    lower = ci / 2.0

    # Technically instead of doing ci / 2.0 we should do something like this:
    # ci = np.linspace(0, 80, 50)
    # fval = np.zeros(50)
    # for i in range(50):
    #     fval[i] = f(ci[i])
    #     if fval[i] < -1:
    #         lower = ci[i]

    # fig = go.Figure()
    # fig.add_trace(go.Scatter(x=ci, y=fval))
    # fig.update_layout(title="ci_func", xaxis_title="ci", yaxis_title="fval")
    # fig.write_image("./fig4.png")

    sol = root_scalar(f, bracket=[lower, 90.0], method="brentq", rtol=1e-2)

    return sol.root


def main(ci, lmr_z, par_z, gb_mol, je, cair, oair, rh_can, p, iv, c):
    f = root_func(lmr_z, par_z, gb_mol, je, cair, oair, rh_can, p, iv, c)

    ci_val = solve_ci(ci, f)

    _, gs_mol, an = ci_func(
        ci_val,
        lmr_z,
        par_z,
        gb_mol,
        je,
        cair,
        oair,
        rh_can,
        p,
        iv,
        c,
        c3flag=True,
        stomatalcond_mtd=1,
    )

    return ci_val, gs_mol
