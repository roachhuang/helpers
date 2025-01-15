import numpy as np

def test_run():
    # generate an array full of random numbers, uniformly sampled from [0.0, 1.0]
    np.random.random((5,4)) # 5 rows and 4 cols. not that its fn arguments is a tuple
    np.random.rand(5,4) # fun arg isn't a tuple   
    # above 2 fn get the same retruns

    np.random.normal(size=(2,3))    # std normal (mean=0, std=1)
    # mean=50, std=10
    np.random.normal(50, 10, size=(2,3))
    
    # random integers. btw 0 and 10
    a=np.random.randint(0, 10, size=(2,3))

    # for each col sum all the values of each row of that col, so you would essentially iterate over the rows
    # hence we pass axis=0 to compute col sums 
    a.sum(axis=0)
    a.min(axis=1)
    a.mean()    # leave out axis arg. ret mean of all elements
    # return the idex of max value
    idx=a.argmax()

    element = a[3,2]  
    a[0, 1:3]
    # n:m:t specifies a range that starts at n, and stops before m, in steps of size t
    a[:, 0:3:2] # will select cols 0, 2 for every row t

    # accessing using list of indices
    indices = np.array([1,1,2,3])
    a[indices]

    mean=a.mean()
    a[a<mean]=mean

    # global statistics for each stock

   