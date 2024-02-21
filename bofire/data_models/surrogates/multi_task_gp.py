from typing import Annotated, Literal, Optional

import pandas as pd
from pydantic import Field

from bofire.data_models.domain.api import Inputs
from bofire.data_models.enum import RegressionMetricsEnum
from bofire.data_models.features.api import CategoricalInput
from bofire.data_models.kernels.api import (
    AnyKernel,
    MaternKernel,
    RBFKernel,
)
from bofire.data_models.priors.api import (
    BOTORCH_LENGTHCALE_PRIOR,
    BOTORCH_LKJ_PRIOR,
    BOTORCH_NOISE_PRIOR,
    MBO_LENGTHCALE_PRIOR,
    MBO_NOISE_PRIOR,
    AnyPrior,
)
from bofire.data_models.priors.lkj import LKJPrior

# from bofire.data_models.strategies.api import FactorialStrategy
from bofire.data_models.surrogates.trainable import Hyperconfig
from bofire.data_models.surrogates.trainable_botorch import TrainableBotorchSurrogate


class MultiTaskGPHyperconfig(Hyperconfig):
    type: Literal["MultiTaskGPHyperconfig"] = "MultiTaskGPHyperconfig"
    inputs: Inputs = Inputs(
        features=[
            CategoricalInput(
                key="kernel", categories=["rbf", "matern_1.5", "matern_2.5"]
            ),
            CategoricalInput(key="prior", categories=["mbo", "botorch"]),
            CategoricalInput(key="ard", categories=["True", "False"]),
        ]
    )
    target_metric: RegressionMetricsEnum = RegressionMetricsEnum.MAE
    hyperstrategy: Literal[
        "FactorialStrategy", "SoboStrategy", "RandomStrategy"
    ] = "FactorialStrategy"

    @staticmethod
    def _update_hyperparameters(
        surrogate_data: "MultiTaskGPSurrogate", hyperparameters: pd.Series
    ):
        def matern_25(ard: bool, lengthscale_prior: AnyPrior) -> MaternKernel:
            return MaternKernel(nu=2.5, lengthscale_prior=lengthscale_prior, ard=ard)

        def matern_15(ard: bool, lengthscale_prior: AnyPrior) -> MaternKernel:
            return MaternKernel(nu=1.5, lengthscale_prior=lengthscale_prior, ard=ard)

        if hyperparameters.prior == "mbo":
            noise_prior, lengthscale_prior = (MBO_NOISE_PRIOR(), MBO_LENGTHCALE_PRIOR())
        else:
            noise_prior, lengthscale_prior = (
                BOTORCH_NOISE_PRIOR(),
                BOTORCH_LENGTHCALE_PRIOR(),
            )

        surrogate_data.noise_prior = noise_prior
        if hyperparameters.kernel == "rbf":
            surrogate_data.kernel = (
                RBFKernel(ard=hyperparameters.ard, lengthscale_prior=lengthscale_prior),
            )
        elif hyperparameters.kernel == "matern_2.5":
            surrogate_data.kernel = matern_25(
                ard=hyperparameters.ard, lengthscale_prior=lengthscale_prior
            )
        elif hyperparameters.kernel == "matern_1.5":
            surrogate_data.kernel = matern_15(
                ard=hyperparameters.ard, lengthscale_prior=lengthscale_prior
            )
        else:
            raise ValueError(f"Kernel {hyperparameters.kernel} not known.")


class MultiTaskGPSurrogate(TrainableBotorchSurrogate):
    type: Literal["MultiTaskGPSurrogate"] = "MultiTaskGPSurrogate"
    n_tasks: Annotated[int, Field(ge=1)] = 1
    kernel: AnyKernel = Field(
        default_factory=lambda: MaternKernel(
            ard=True,
            nu=2.5,
            lengthscale_prior=BOTORCH_LENGTHCALE_PRIOR(),
        )
    )
    noise_prior: AnyPrior = Field(default_factory=lambda: BOTORCH_NOISE_PRIOR())
    lkj_prior: LKJPrior = Field(default_factory=lambda: BOTORCH_LKJ_PRIOR())
    hyperconfig: Optional[MultiTaskGPHyperconfig] = Field(
        default_factory=lambda: MultiTaskGPHyperconfig()
    )