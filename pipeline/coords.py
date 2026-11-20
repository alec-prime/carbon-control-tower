import math
C={'Abu Dhabi':(24.45,54.38),'Athens':(37.98,23.73),'Beijing':(39.90,116.40),'Dubai':(25.20,55.27),'Istanbul':(41.01,28.98),'Moscow':(55.76,37.62),'New Delhi':(28.61,77.21),'New York':(40.71,-74.01),'Shanghai':(31.23,121.47),'Sydney':(-33.87,151.21),'Berlin':(52.52,13.40),'Amsterdam':(52.37,4.90),'London':(51.51,-0.13),'Madrid':(40.42,-3.70),'Paris':(48.86,2.35),'Rome':(41.90,12.50),'Cape Town':(-33.92,18.42),'Johannesburg':(-26.20,28.05),'Copenhagen':(55.68,12.57),'Dallas':(32.78,-96.80),'Tokyo':(35.68,139.69),'Doha':(25.29,51.53),'Frankfurt':(50.11,8.68),'Fukuoka':(33.59,130.40),'Hamburg':(53.55,9.99),'Lisbon':(38.72,-9.14),'Mexico City':(19.43,-99.13),'Miami':(25.76,-80.19),'Reykjavik':(64.15,-21.94),'Toronto':(43.65,-79.38),'Singapore':(1.35,103.82),'Auckland':(-36.85,174.76),'Brisbane':(-27.47,153.03),'Los Angeles':(34.05,-118.24),'Melbourne':(-37.81,144.96),'Perth':(-31.95,115.86),'São Paulo':(-23.55,-46.63),'Buenos Aires':(-34.60,-58.38)}
def hv(p,q):
    (a1,b1),(a2,b2)=C[p],C[q];r=math.radians
    d=math.sin(r(a2-a1)/2)**2+math.cos(r(a1))*math.cos(r(a2))*math.sin(r(b2-b1)/2)**2
    return 2*6371*math.asin(math.sqrt(d))
