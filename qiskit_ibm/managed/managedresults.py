# This code is part of Qiskit.
#
# (C) Copyright IBM 2019.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Results managed by the Job Manager."""

from typing import List, Optional, Union, Tuple, Dict
import copy

import numpy  # pylint: disable=unused-import
from qiskit.result import Result
from qiskit.circuit import QuantumCircuit
from qiskit.pulse import Schedule

from qiskit_ibm.managed import managedjobset  # pylint: disable=unused-import
from .exceptions import IBMQManagedResultDataNotAvailable
from ..job.exceptions import JobError


class ManagedResults:
    """Results managed by the Job Manager.

    This class is a wrapper around the :class:`~qiskit.result.Result` class and
    provides the same methods. Please refer to the
    :class:`~qiskit.result.Result` class for more information on the methods.
    """

    def __init__(
            self,
            job_set: 'managedjobset.ManagedJobSet',
            backend_name: str,
            success: bool
    ):
        """ManagedResults constructor.

        Args:
            job_set: Managed job set for these results.
            backend_name: Name of the backend used to run the experiments.
            success: ``True`` if all experiments were successful and results
                available. ``False`` otherwise.

        Attributes:
            backend_name: Name of the backend used to run the experiments.
            success: Whether all experiments were successful.
        """
        self._job_set = job_set
        self.backend_name = backend_name
        self.success = success
        self._combined_results = None  # type: Optional[Result]

    def data(self, experiment: Union[str, QuantumCircuit, Schedule, int]) -> Dict:
        """Get the raw data for an experiment.

        Args:
            experiment: Retrieve result for this experiment. Several types are
                accepted for convenience:

                    * str: The name of the experiment.
                    * QuantumCircuit: The name of the circuit instance will be used.
                    * Schedule: The name of the schedule instance will be used.
                    * int: The position of the experiment.

        Returns:
            Refer to the :meth:`Result.data()<qiskit.result.Result.data()>` for
            information on return data.

        Raises:
            IBMQManagedResultDataNotAvailable: If data for the experiment could not be retrieved.
            IBMQJobManagerJobNotFound: If the job for the experiment could not
                be found.
        """
        result, exp_index = self._get_result(experiment)
        return result.data(exp_index)

    def get_memory(
            self,
            experiment: Union[str, QuantumCircuit, Schedule, int]
    ) -> Union[list, 'numpy.ndarray']:
        """Get the sequence of memory states (readouts) for each shot.
        The data from the experiment is a list of format
        ['00000', '01000', '10100', '10100', '11101', '11100', '00101', ..., '01010']

        Args:
            experiment: Retrieve result for this experiment, as specified by :meth:`data()`.

        Returns:
            Refer to the :meth:`Result.get_memory()<qiskit.result.Result.get_memory()>`
            for information on return data.

        Raises:
            IBMQManagedResultDataNotAvailable: If data for the experiment could not be retrieved.
            IBMQJobManagerJobNotFound: If the job for the experiment could not
                be found.
        """
        result, exp_index = self._get_result(experiment)
        return result.get_memory(exp_index)

    def get_counts(
            self,
            experiment: Union[str, QuantumCircuit, Schedule, int]
    ) -> Dict[str, int]:
        """Get the histogram data of an experiment.

        Args:
            experiment: Retrieve result for this experiment, as specified by :meth:`data()`.

        Returns:
            Refer to the :meth:`Result.get_counts()<qiskit.result.Result.get_counts()>`
            for information on return data.

        Raises:
            IBMQManagedResultDataNotAvailable: If data for the experiment could not be retrieved.
            IBMQJobManagerJobNotFound: If the job for the experiment could not
                be found.
        """
        result, exp_index = self._get_result(experiment)
        return result.get_counts(exp_index)

    def get_statevector(
            self,
            experiment: Union[str, QuantumCircuit, Schedule, int],
            decimals: Optional[int] = None
    ) -> List[complex]:
        """Get the final statevector of an experiment.

        Args:
            experiment: Retrieve result for this experiment, as specified by :meth:`data()`.
            decimals: The number of decimals in the statevector.
                If ``None``, skip rounding.

        Returns:
            Refer to the :meth:`Result.get_statevector()<qiskit.result.Result.get_statevector()>`
            for information on return data.

        Raises:
            IBMQManagedResultDataNotAvailable: If data for the experiment could not be retrieved.
            IBMQJobManagerJobNotFound: If the job for the experiment could not
                be found.
        """
        result, exp_index = self._get_result(experiment)
        return result.get_statevector(experiment=exp_index, decimals=decimals)

    def get_unitary(
            self,
            experiment: Union[str, QuantumCircuit, Schedule, int],
            decimals: Optional[int] = None
    ) -> List[List[complex]]:
        """Get the final unitary of an experiment.

        Args:
            experiment: Retrieve result for this experiment, as specified by :meth:`data()`.
            decimals: The number of decimals in the unitary.
                If ``None``, skip rounding.

        Returns:
            Refer to the :meth:`Result.get_unitary()<qiskit.result.Result.get_unitary()>`
            for information on return data.

        Raises:
            IBMQManagedResultDataNotAvailable: If data for the experiment could not be retrieved.
            IBMQJobManagerJobNotFound: If the job for the experiment could not
                be found.
        """
        result, exp_index = self._get_result(experiment)
        return result.get_unitary(experiment=exp_index, decimals=decimals)

    def combine_results(self) -> Result:
        """Combine results from all jobs into a single `Result`.

        Note:
            Since the order of the results must match the order of the initial
            experiments, job results can only be combined if all jobs succeeded.

        Returns:
            A :class:`~qiskit.result.Result` object that contains results from
                all jobs.
        Raises:
            IBMQManagedResultDataNotAvailable: If results cannot be combined
                because some jobs failed.
        """
        if self._combined_results:
            return self._combined_results

        if not self.success:
            raise IBMQManagedResultDataNotAvailable(
                "Results cannot be combined since some of the jobs failed.")

        jobs = self._job_set.jobs()
        combined_result = copy.deepcopy(jobs[0].result())
        for idx in range(1, len(jobs)):
            combined_result.results.extend(jobs[idx].result().results)

        self._combined_results = combined_result
        return combined_result

    def _get_result(
            self,
            experiment: Union[str, QuantumCircuit, Schedule, int]
    ) -> Tuple[Result, int]:
        """Get the result of the job used to submit the experiment.

        Args:
            experiment: Retrieve result for this experiment, as specified by :meth:`data()`.

        Returns:
            A tuple of the result of the job used to submit the experiment and
                the experiment index within the job.

        Raises:
            IBMQManagedResultDataNotAvailable: If data for the experiment could not be retrieved.
            IBMQJobManagerJobNotFound: If the job for the experiment could not
                be found.
        """

        (job, exp_index) = self._job_set.job(experiment)
        if job is None:
            raise IBMQManagedResultDataNotAvailable(
                'Job for experiment {} was not successfully submitted.'.format(experiment))

        try:
            result = job.result()
            return result, exp_index
        except JobError as err:
            raise IBMQManagedResultDataNotAvailable(
                'Result data for experiment {} is not available.'.format(experiment)) from err
