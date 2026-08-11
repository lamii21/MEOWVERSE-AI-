# Dataset License & Attribution

## Oxford-IIIT Pet Dataset

- **Source:** https://www.robots.ox.ac.uk/~vgg/data/pets/
- **Paper:** O. M. Parkhi, A. Vedaldi, A. Zisserman, C. V. Jawahar,
  "Cats and Dogs", IEEE Conference on Computer Vision and Pattern
  Recognition, 2012.
- **License:** Creative Commons Attribution-ShareAlike 4.0
  International (CC BY-SA 4.0) for both images and annotations, per
  the dataset's official page.

MeowVerse AI uses only the **12 cat breeds** from this 37-breed
dataset (the remaining 25 are dog breeds) for the breed classifier in
`ml/training/train_breed_classifier.py`. Downloaded and processed via
`ml/scripts/prepare_dataset.py`, which writes derived, resplit copies
to `ml/dataset/processed/` (gitignored — regenerate locally by running
the script; not redistributed in this repository).

Per CC BY-SA 4.0, any redistribution of this dataset or derivatives
must retain this attribution and license notice.
