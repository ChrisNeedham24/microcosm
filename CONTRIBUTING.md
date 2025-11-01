# Contributions

For those wishing to contribute, welcome and good luck.

### Links

- [Wiki](https://github.com/ChrisNeedham24/microcosm/wiki)
- [Issues](https://github.com/ChrisNeedham24/microcosm/issues)
- [Discussions](https://github.com/ChrisNeedham24/microcosm/discussions)

### Testing

Tests in this repository use the built-in `unittest` library as well as the [coverage](https://pypi.org/project/coverage/) library.

To run the tests, the following command can be run from the project's root directory: `python -m unittest discover -s source/tests -t source/tests`

Alternatively, to run the tests with coverage enabled, you can run the following command from the project's root directory: `coverage run -m unittest discover -s source/tests/ -t source/tests/`. You can then generate a coverage report using `coverage report -m`.

All business logic and functional code requires unit testing, while display-related code does not.
A good rule of thumb is if the function has multiple references to `pyxel` in it, it does not require testing.

100% coverage of functional code is required to pass the coverage CI check.

If you create a new function with drawing code, you can add its signature to `.coveragerc` to exempt it from coverage checks.
Alternatively, you can use the `# pragma: no cover` comment to do the same thing without modifying the config file.

### Environment details

To contribute to Microcosm, first create a fork of the repository into your own GitHub account.
For development, Python 3.12 as well as the requirements defined in dev_requirements.txt are needed.

Please note that all changes should be made on a branch *other* than main.

### Submitting pull requests

When you're satisfied that you have completed an issue, or have made another valuable contribution, put up a pull request for review.
You should receive a response in a day or two, and a full review by the weekend at the latest.

### If you find a bug

Hey, none of us are perfect. So, if you find a bug in the game, add a new issue [here](https://github.com/ChrisNeedham24/microcosm/issues/new).
Any submitted issues of this kind should have the bug label, so be sure to mention in the issue description that the label should be applied.

If you're not sure whether something classifies as a bug, just suggest the 'almost a bug' label instead.

### What to try first

Any issue with either of the 'hacktoberfest' or 'good first issue' labels will be a good start.

### Additional features

If you have a dream for Microcosm that isn't adequately captured in existing issues, add a new issue [here](https://github.com/ChrisNeedham24/microcosm/issues/new).
If you think the feature may require some significant work, be sure to mention that in the issue description as well.

### Style guide

Microcosm broadly follows [PEP-8](https://peps.python.org/pep-0008/) styling.
Pylint is also used to guarantee conformity.
If you're ever unsure whether you've formatted something correctly, run `pylint $(git ls-files '*.py')`.

### Code of Conduct

See [here](/CODE-OF-CONDUCT.md) for the repository's Code of Conduct.
