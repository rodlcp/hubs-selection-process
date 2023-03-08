# Hubs Selection Process

This repository is destined to my solution to the proposed challenge and contains the following files:

 - `analyse_holes.py`: Python script with the code that reads the file, transforms it and generates the outputs;
 - `basic_insights.xlsx`: basic insights generated with the code;
 - `erd.png`: an image containing the ERD of the received data;
 - `transformation_pipeline_diagram.png`: an image with the general idea of the steps applied on the data to transform it and arrive at the final solution.

# General Idea
The goal is to determine if the parts have any unreachable holes (a hole that is not easy to manufacture). To achieve such result we are first going to analyse each hole individually and verify if it's an unreachable hole, after that we will check for each object if any of its holes are unreachable, and finally merge the 2 new columns into the original data, stating if the object have an unreachable hole warning and/or error.

In this process we are also going to extract some basic information like:
- Data types and sizes;
- Total amount of objects;
- Total amount of objects with unreachable holes;
- Total amount of holes;
- Total amount of unreachable holes;
- Distributions regarding holes' length, radius, volume, ratio, holes per object and unreachable holes per object.

Some assumptions made in this work:
- The data is processed in "big" batches;
- The batches fit in computer memory;
- The radius of a hole is never 0.

# Results
The results show that only 2% of the objects have a poor ratio between length and radius of its holes, and 0.2% have a critical ratio. Also, 44% of the objects with an unreachable hole have more than one unreachable hole.

The average amount of holes per object is 13 while the median is 5, the maximum amount of holes in one object is 2,695. The median hole has a volume of 66 mm³ while the biggest hole has a volume of 243 m³. The median ratio between length and radius is 2.29 while the average is 4.08, the most critical hole has a ratio of 934.35.