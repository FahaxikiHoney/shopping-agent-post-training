# Dataset card

## Summary

This repository includes curated shopping-agent examples in `sft_data/ready_to_run/`: ChatML v3 SFT records (1,297 train / 142 validation), ShareGPT-style ReAct records (875 train / 100 eval / 100 test), 875 converted Slime task prompts, a 100-query sample, and cleaned/scored trajectory examples.

## Intended use

The records are provided to demonstrate and reproduce the repository's data formats, evaluation flow, and post-training examples. Product and retailer references may appear as part of the task domain. The mock product tools use local fixtures and do not connect to a live retail service.

## Data creation and provenance

The files are curated and transformed for this project. Records containing the Unicode replacement character (unrecoverable text encoding damage) were removed from release datasets. Order identifiers, shipping tracking identifiers, and retailer deep links were redacted in the released text datasets. Before publication, review each included split for redistribution rights and provenance. The MIT license at the repository root applies to project code; it does not automatically grant rights to the data, model outputs, names, trademarks, or third-party material contained in these files.

## Privacy and sensitive information

Raw internal trajectory collection directories are not included. The release should contain no credentials, direct personal contact details, real delivery addresses, or private customer/order records. The repository's automated scanner is a heuristic and cannot prove that data is safe to publish; inspect the final data bundle manually and remove any questionable record.

## Known limitations

- Samples may contain generated or mock product facts and should not be treated as live price, availability, or product advice.
- Model-generated reasoning and labels can be incorrect or inconsistent.
- Training/evaluation results depend on the exact base model, prompt, framework revision, hardware, and configuration.
- Data splits are intended for project experiments; they are not a benchmark with independently verified ground truth.

## Files

See [`sft_data/ready_to_run/README.md`](sft_data/ready_to_run/README.md) for file-level counts and use, and [`docs/01-data-pipeline.md`](docs/01-data-pipeline.md) for schema details.
