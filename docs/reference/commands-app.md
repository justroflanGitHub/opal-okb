# Категория app

3 команды.

| Команда | Описание | Параметры | Returns |
| --- | --- | --- | --- |
| [`app.env`](#appenv) | Окружение исполнения: версия/реализация Python, ОС, кодировка stdout, доступность и версии расчётных пакетов (numpy, matplotlib) | — | {python, python_implementation, executable, os, os_release, machine, stdout_encoding, filesystem_encoding, packages: {имя: {available, version}}} |
| [`app.info`](#appinfo) | Сведения о приложении: имя и версия проекта (верхний релиз CHANGELOG.md), Python, платформа, счётчики этого реестра | — | {project, version, version_source, python, platform, registry: {total, num_categories}} |
| [`app.paths`](#apppaths) | Каталоги данных проекта (из констант catalog.library): корень, OPJ-системы, LBO-библиотеки; наличие каталогов и число файлов в них | — | {project_root, base_dir, opj_dir, lbo_dir, opj_dir_exists, lbo_dir_exists, num_opj_files, num_lbo_files, cwd} |

## Параметры и результаты

### app.env

Окружение исполнения: версия/реализация Python, ОС, кодировка stdout, доступность и версии расчётных пакетов (numpy, matplotlib)

**Returns:** {python, python_implementation, executable, os, os_release, machine, stdout_encoding, filesystem_encoding, packages: {имя: {available, version}}}

### app.info

Сведения о приложении: имя и версия проекта (верхний релиз CHANGELOG.md), Python, платформа, счётчики этого реестра

**Returns:** {project, version, version_source, python, platform, registry: {total, num_categories}}

### app.paths

Каталоги данных проекта (из констант catalog.library): корень, OPJ-системы, LBO-библиотеки; наличие каталогов и число файлов в них

**Returns:** {project_root, base_dir, opj_dir, lbo_dir, opj_dir_exists, lbo_dir_exists, num_opj_files, num_lbo_files, cwd}

