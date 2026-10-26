# Shared opening and closing

All five body templates use this layout. Replace every `{{...}}` with verified
project content; omit an optional line when its asset or destination does not
exist. These placeholders are authoring instructions, never finished README
content. Use paths relative to the README, not relative to this reference.

## Opening

Keep the blank lines: they let GitHub parse the Markdown inside the HTML
container. The closing `</div>` comes before the first body section.

```markdown
<div align="center">

<img src="{{logo_path}}" alt="{{project_name}} logo" width="160">

# {{project_name}}

**{{core_use_and_value}}**

{{short_supporting_description}}

[![{{badge_label}}]({{badge_image_url}})]({{badge_target_url}})

[{{download_label}}]({{download_url}}) · [{{docs_label}}]({{docs_path}}) · [简体中文](README.md) · [English](README.en.md)

</div>
```

The logo size is an example, not a requirement. Repeat the badge link for real
badges, keeping them in one row or splitting status and platform badges into two
rows. Keep meaningful alt text. The navigation may include existing examples
or community links instead; do not create destinations to match this sample.
Do not add a sponsor row unless the user requested one and supplied its facts.

## Closing

This follows the order and restrained tone of
[WeChatBridge](https://github.com/freestylefly/WeChatBridge#许可证). Replace the
licence path if the real file has another name. If no licence is declared,
replace the sentence with that fact and omit any licence badge. Omit Credits
when no acknowledgement is supported. Use the final Star line only for a public
GitHub project.

```markdown
## License

{{project_name}} is released under the [{{license_name}}]({{license_path}}).

## Credits

- [{{source_name}}]({{source_url}}): {{specific_contribution}}.

<p align="center"><sub>If this project helps you, a ⭐ can help others discover it.</sub></p>
```

For Chinese, use `## 许可证` and `## 致谢`, write the licence and contribution
sentences naturally, and keep the same source links and facts. A suitable last
line is:

```html
<p align="center"><sub>如果这个项目对你有帮助，欢迎点亮 ⭐，让更多有同样需求的人发现它。</sub></p>
```
