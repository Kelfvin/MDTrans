use std::path::PathBuf;

use anyhow::{Result, bail};
use walkdir::WalkDir;

pub fn resolve_pdf_path(pdf_path_arg: &str) -> Result<PathBuf> {
    let pdf_path = PathBuf::from(pdf_path_arg).canonicalize()?;
    if !pdf_path.is_file() {
        bail!("Input PDF is not a file: {}", pdf_path.display());
    }
    Ok(pdf_path)
}

pub fn resolve_output_dir(output_dir_arg: &str) -> Result<PathBuf> {
    let path = PathBuf::from(output_dir_arg);
    if path.exists() {
        Ok(path.canonicalize()?)
    } else {
        Ok(path)
    }
}

pub fn find_markdown(path: PathBuf) -> Result<Vec<PathBuf>> {
    if path.is_file() {
        if is_source_markdown(&path) {
            return Ok(vec![path]);
        }
        bail!("Input is not a source Markdown file: {}", path.display());
    }

    if !path.is_dir() {
        bail!(
            "Input path does not exist or is not a directory: {}",
            path.display()
        );
    }

    let mut files = Vec::new();
    for entry in WalkDir::new(&path)
        .into_iter()
        .filter_map(|entry| entry.ok())
    {
        if !entry.file_type().is_file() {
            continue;
        }

        let file_path = entry.into_path();
        if is_source_markdown(&file_path) {
            files.push(file_path);
        }
    }

    files.sort();

    if files.is_empty() {
        bail!("No Markdown files found under {}", path.display());
    }

    Ok(files)
}

fn is_source_markdown(path: &PathBuf) -> bool {
    path.extension().is_some_and(|ext| ext == "md")
        && path
            .file_name()
            .is_some_and(|name| !name.to_string_lossy().ends_with(".zh.md"))
}

#[cfg(test)]
mod tests {
    use std::time::{SystemTime, UNIX_EPOCH};

    use super::*;

    fn temp_dir(name: &str) -> PathBuf {
        let unique = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_nanos();
        std::env::temp_dir().join(format!("transmd-{name}-{unique}"))
    }

    #[test]
    fn returns_single_markdown_file() {
        let dir = temp_dir("single-md");
        std::fs::create_dir_all(&dir).unwrap();
        let file = dir.join("doc.md");
        std::fs::write(&file, "# hello").unwrap();

        let result = find_markdown(file.clone()).unwrap();
        assert_eq!(result, vec![file]);

        let _ = std::fs::remove_dir_all(dir);
    }

    #[test]
    fn rejects_translated_markdown_file() {
        let dir = temp_dir("translated-md");
        std::fs::create_dir_all(&dir).unwrap();
        let file = dir.join("doc.zh.md");
        std::fs::write(&file, "# hello").unwrap();

        let error = find_markdown(file).unwrap_err().to_string();
        assert!(error.contains("not a source Markdown file"));

        let _ = std::fs::remove_dir_all(dir);
    }

    #[test]
    fn finds_all_markdown_recursively_and_excludes_translated_files() {
        let dir = temp_dir("recursive");
        let nested = dir.join("nested");
        std::fs::create_dir_all(&nested).unwrap();
        let first = dir.join("a.md");
        let second = nested.join("b.md");
        let translated = nested.join("b.zh.md");
        std::fs::write(&first, "# a").unwrap();
        std::fs::write(&second, "# b").unwrap();
        std::fs::write(&translated, "# zh").unwrap();

        let result = find_markdown(dir.clone()).unwrap();
        assert_eq!(result, vec![first, second]);

        let _ = std::fs::remove_dir_all(dir);
    }

    #[test]
    fn errors_when_directory_has_no_source_markdown() {
        let dir = temp_dir("empty");
        std::fs::create_dir_all(&dir).unwrap();
        std::fs::write(dir.join("doc.zh.md"), "# zh").unwrap();

        let error = find_markdown(dir.clone()).unwrap_err().to_string();
        assert!(error.contains("No Markdown files found"));

        let _ = std::fs::remove_dir_all(dir);
    }
}
