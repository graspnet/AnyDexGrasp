import unittest
import gc
import operator as op
import functools
import torch
from torch.autograd import Variable, Function
from knn_pytorch import knn_pytorch
# import knn_pytorch
def knn(ref, query, k=1):
  """ Compute k nearest neighbors for each query point.
  """
  device = ref.device
  ref = ref.float().to(device)
  query = query.float().to(device)
  inds = torch.empty(query.shape[0], k, query.shape[2]).long().to(device)
  knn_pytorch.knn(ref, query, inds)
  return inds


class TestKNearestNeighbor(unittest.TestCase):

  def test_forward(self):
    knn = KNearestNeighbor(2)
    while(1):
        D, N, M = 128, 100, 1000
        ref = Variable(torch.rand(2, D, N))
        query = Variable(torch.rand(2, D, M))

        inds = knn(ref, query)
        for obj in gc.get_objects():
            if torch.is_tensor(obj):
                print(functools.reduce(op.mul, obj.size()) if len(obj.size()) > 0 else 0, type(obj), obj.size())
        #ref = ref.cpu()
        #query = query.cpu()
        print(inds)


if __name__ == '__main__':
  unittest.main()
