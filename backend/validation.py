# -*- coding: utf-8 -*-
#
# validation.py
#

"""
Tools to compare the contentes of the references clusters to the contents of
the predicted biclusters.
"""

__author__ = 'Severin E. R. Langberg'
__email__ = 'Langberg91@gmail.no'


import os
import ast

import metrics

import numpy as np
import pandas as pd


def recovery_score(true, pred):
    """The percentage of true items among the predicted
    items."""


    frac = np.isin(pred, true).sum() / np.size(true)

    return np.round(frac * 100, decimals=3)


def relevance_score(true, pred):
    """The percentage the true predicted items
    constitute in the total predicted population."""

    if np.size(pred) > 0:
        frac = np.isin(true, pred).sum() / np.size(pred)
        result = np.round(frac * 100, decimals=1)
    else:
        result = 0.0

    return result


def compare_clusters(pred_cluster, target_cluster):

    cpgs, genes = pred_cluster.labels

    scores = np.zeros((len(cpgs) * 2, 4), dtype=float)

    prev = 0
    for num, _cpgs in enumerate(cpgs):

        cpg_id, gene_id = (num + prev), (num + prev + 1)

        scores[cpg_id, 0] = recovery_score(target_cluster.cpgs1, _cpgs)
        scores[cpg_id, 1] = relevance_score(target_cluster.cpgs1, _cpgs)
        scores[cpg_id, 2] = recovery_score(target_cluster.cpgs2, _cpgs)
        scores[cpg_id, 3] = relevance_score(target_cluster.cpgs2, _cpgs)

        scores[gene_id, 0] = recovery_score(target_cluster.genes1, genes[num])
        scores[gene_id, 1] = relevance_score(target_cluster.genes1, genes[num])
        scores[gene_id, 2] = recovery_score(target_cluster.genes2, genes[num])
        scores[gene_id, 3] = relevance_score(target_cluster.genes2, genes[num])

        prev += 1

    idx = pd.MultiIndex.from_product(
        [('ref1', 'ref2'), ('recovery', 'relevance')],
        names=('cluster', 'score')
    )
    cols = pd.MultiIndex.from_product(
        [np.arange(num + 1) + 1, ('cpgs', 'genes')],
        names=('num', 'kind')
    )
    df = pd.DataFrame(scores.T, index=idx, columns=cols)

    return df


def _external_metrics(indicators, nbiclusters, data):
    # Utility function for computing external metrics.

    row_idx, col_idx = indicators

    scores = {}
    for num in range(nbiclusters):

        _row_cluster = data.values[row_idx[num], :]
        cluster = _row_cluster[:, col_idx[num]]
        if np.any(cluster):
            scores[num] = {
                'msr': metrics.mean_squared_residue(cluster),
                'smsr': metrics.scaled_mean_squared_residue(cluster),
                'tve': metrics.transposed_virtual_error(cluster),
                #'shift_scale': metrics.avg_spearmans_rho(cluster)
            }
        else:
            pass

    df_scores = pd.DataFrame(scores).T
    df_scores.index.name = 'num'

    return df_scores


class References:
    """Representation of a set of reference biclsuters."""

    @classmethod
    def from_files(cls, path_to_cpgs, path_to_genes, num_ref_clusters=2):

        # Read target CpG data.
        target_cpgs = {str(num + 1): [] for num in range(num_ref_clusters)}
        with open(path_to_cpgs, 'r') as cpgfile:

            cpg_contents = cpgfile.read().split('\n')
            # Skip header line.
            for row in cpg_contents[1:]:
                try:
                    value, idx, _ = row.split()
                    target_cpgs[idx].append(ast.literal_eval(value))
                except:
                    pass

        # Read target gene data.
        target_genes = {str(num + 1): [] for num in range(num_ref_clusters)}
        with open(path_to_genes, 'r') as genefile:

            gene_contents = genefile.read().split('\n')
            # Skip header line.
            for row in gene_contents[1:]:
                try:
                    value, idx = row.split()
                    target_genes[idx].append(ast.literal_eval(value))
                except:
                    pass

        return References(cpgs=target_cpgs, genes=target_genes)

    def __init__(self, cpgs, genes):

        self.cpgs = cpgs
        self.genes = genes

    @property
    def cpgs1(self):

        return self.cpgs['1']

    @property
    def cpgs2(self):

        return self.cpgs['2']

    @property
    def genes1(self):

        return self.genes['1']

    @property
    def genes2(self):

        return self.genes['2']

    def external_metrics(self, data):

        cl1 = data.loc[self.cpgs1, self.genes1]
        cl2 = data.loc[self.cpgs2, self.genes2]

        scores = {}
        for num, cluster in enumerate([cl1, cl2]):
            scores[num] = {
                'msr': metrics.mean_squared_residue(
                    cluster.values
                ),
                'smsr': metrics.scaled_mean_squared_residue(
                    cluster.values
                ),
                'tve': metrics.transposed_virtual_error(
                    cluster.values
                ),
                #'shift_scale': metrics.avg_spearmans_rho(cluster)
            }
        df_scores = pd.DataFrame(scores).T
        df_scores.index = ('ref_cluster1', 'ref_cluster2')

        return df_scores


class Biclusters:
    """Representation of a set of predicted
    biclusters."""

    def __init__(self, rows, cols, data):

        self.rows = rows
        self.cols = cols
        self.data = data

        # NOTE: Sets attributes.
        self._setup()

    @property
    def nbiclusters(self):

        return self._nbiclusters

    @nbiclusters.setter
    def nbiclusters(self, value):

        if np.shape(self.rows)[0] == np.shape(self.cols)[0]:
            self._nbiclusters = value
        else:
            raise RuntimeError('Sample clusters: {}, ref clusters {}'
                               ''.format(sample, ref))

    def _setup(self):

        self.nrows, self.ncols = np.shape(self.data)
        self.nbiclusters = np.shape(self.rows)[0]

        return self

    @property
    def indicators(self):
        """Determine coordiantes of row and column indicators
        for each bicluster.
        """

        row_idx, col_idx = [], []
        for cluster_num in range(self.nbiclusters):

            rows_bools = self.rows[cluster_num, :] != 0
            cols_bools = self.cols[cluster_num, :] != 0

            rows = [index for index, elt in enumerate(rows_bools) if elt]
            cols = [index for index, elt in enumerate(cols_bools) if elt]

            row_idx.append(rows), col_idx.append(cols)

        return row_idx, col_idx

    @property
    def stats(self):
        """Compute max, min and std from data points
        included in biclusters.
        """

        row_idx, col_idx = self.indicators
        data_size = np.size(self.data)

        stats = {}
        for num in range(self.nbiclusters):

            _row_cluster = self.data.values[row_idx[num], :]
            cluster = _row_cluster[:, col_idx[num]]
            if np.any(cluster):
                cluster_size = np.size(cluster)
                nrows, ncols = np.shape(cluster)

                stats[num + 1] = {
                    'max': np.max(cluster),
                    'min': np.min(cluster),
                    'std': np.std(cluster),
                    'nrows': nrows,
                    'ncols': ncols,
                    #'size': cluster_size,
                    'rel_size': cluster_size / data_size,
                    'zeros': int(np.count_nonzero(cluster==0))
                }
            else:
                pass

        df_stats = pd.DataFrame(stats).T
        df_stats.index.name = 'num'

        return df_stats

    @property
    def labels(self):
        """Assign row and column labels to biclusters."""

        genes = np.array(self.data.columns, dtype=object)
        cpgs =  np.array(self.data.index, dtype=object)

        row_idx, col_idx = self.indicators

        row_labels, col_labels = [], []
        for num in range(self.nbiclusters):
            row_labels.append(cpgs[row_idx[num]])
            col_labels.append(genes[col_idx[num]])

        return row_labels, col_labels

    @property
    def external_metrics(self):
        """Compute external evaluation metrics for each bicluster."""

        return _external_metrics(
            self.indicators, self.nbiclusters, self.data
        )

    def to_disk(self, file_name, parent='./../predictions/biclusters/'):
        """Generate txt files containing row and column indicators for
        detected biclusters associated with different datasets.

        Args:
            file_name (str): Name of file.

        """

        row_labels, col_labels = self.labels
        with open(os.path.join(parent, file_name), 'w') as outfile:
            for num in range(self.nbiclusters):
                outfile.write('bicluster_{0}\n'.format(num))
                outfile.write('{0}\n'.format(row_labels[num]))
                outfile.write('{0}\n'.format(col_labels[num]))

        return self


if __name__ == '__main__':

    path_target_genes = './../data/test/emQTL_Cluster_genes.txt'
    path_target_cpgs = './../data/test/emQTL_Clusters_CpGs.txt'

    import pandas as pd
    from sklearn.datasets import make_biclusters
    from sklearn.datasets import samples_generator as sg
    from sklearn.cluster.bicluster import SpectralCoclustering

    data, rows, columns = make_biclusters(
        shape=(400, 100), n_clusters=5, noise=5,
        shuffle=False, random_state=0
    )
    shuf_data, row_idx, col_idx = sg._shuffle(data, random_state=0)

    model = SpectralCoclustering(n_clusters=5, random_state=0)
    model.fit(shuf_data)

    bics = Biclusters(
        rows=model.rows_, cols=model.columns_, data=pd.DataFrame(data)
    )
    scores = bics.external_metrics

    print(scores)
