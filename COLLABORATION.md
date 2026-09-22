# How This Was Built

I built this with an AI assistant, working through the notebook one section at a time.

The main rule was that I had to be able to follow every step. I'm new to Python, so the code is written for a beginner: plain pandas, no clever one-liners, and comments that say what each block is doing. It's also why `src/` is four separate scripts that hand CSV files to each other instead of one tidy module with imports. Less elegant, much easier to read.

For each section we'd agree on what it was supposed to answer, build it, look at the real output, and write down what it showed before moving on. What turned up in one section decided what the next one would be. The capture rate came out of that. I was looking at the enrollment trend and wanted to know whether the kids were disappearing or just going somewhere else, and the feature got built to answer it.

I set the direction throughout: which questions were worth asking, which sources to trust, what to cut. The assistant handled execution and explained what it was doing along the way. When something turned out to be wrong, we corrected it in the notebook instead of quietly deleting it, so the reasoning is still there to read. Where I didn't understand something, AI assistant helped explain it to me until I did.
