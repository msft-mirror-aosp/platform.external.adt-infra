<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
    <xsl:template match="testsuites">
        <html>
            <head>
                <title>Test Results For <xsl:value-of select="@name" />
                </title>
                <link href="https://cdnjs.cloudflare.com/ajax/libs/material-components-web/14.0.0/material-components-web.min.css" rel="stylesheet" />
                <script src="https://cdnjs.cloudflare.com/ajax/libs/material-components-web/14.0.0/material-components-web.min.js"></script>
                <link href="https://fonts.googleapis.com/icon?family=Material+Icons" rel="stylesheet" />
                <style>
                    :root {
                    --mdc-theme-success: #4CAF50;
                    --mdc-theme-error: #F44336;
                    --mdc-theme-warning: #FF9800;
                    --mdc-theme-info: #2196F3;
                    --mdc-theme-skip: #9E9E9E;
                    }
                    body {
                    font-family: Roboto, sans-serif;
                    margin: 0;
                    padding: 24px;
                    background-color: var(--mdc-theme-background);
                    color: var(--mdc-theme-on-surface);
                    }
                    li.mdc-list-item button {
                    pointer-events: auto;
                    z-index: 1;
                    }
                    .mdc-chip { margin-right: 8px; margin-bottom: 8px; }
                    .mdc-chip.success { background-color: var(--mdc-theme-success); color: #fff; }
                    .mdc-chip.error { background-color: var(--mdc-theme-error); color: #fff; }
                    .mdc-chip.warning { background-color: var(--mdc-theme-warning); color: #000; }
                    .mdc-chip.info { background-color: var(--mdc-theme-info); color: #fff; }
                    .test-result { display: flex; align-items: center; }
                    .test-result__icon { margin-right: 16px; }
                    .test-result__content { flex-grow: 1; }
                    .test-result__toggle { cursor: pointer; }
                    .test-result__details { display: none; margin-top: 16px; }
                </style>
                 <script>
                    function toggleDetails(id) {
                        var details = document.getElementById(id);
                        if (details.style.display === 'none') {
                            details.style.display = 'block';
                        } else {
                            details.style.display = 'none';
                        }
                    }
                    function copyErrorLog(id) {
                        var errorLog = document.getElementById(id);
                        var range = document.createRange();
                        range.selectNode(errorLog);
                        window.getSelection().removeAllRanges();
                        window.getSelection().addRange(range);
                        document.execCommand('copy');
                        window.getSelection().removeAllRanges();

                        // Visual feedback
                        var copyButton = document.querySelector(`button[data-target="${id}"]`);
                        var originalHTML = copyButton.innerHTML;
                        copyButton.innerHTML = '<span class="mdc-button__ripple"></span><i class="material-icons mdc-button__icon" aria-hidden="true">check</i><span class="mdc-button__label">Copied!</span>';
                        setTimeout(function() {
                          copyButton.innerHTML = originalHTML;
                        }, 2000);
                      }
            </script>
            </head>
            <body class="mdc-typography">
                <h1 class="mdc-typography--headline2">Test Results Summary</h1>
                <xsl:variable name="tests" select="count(//testsuite/testcase)" />
                <xsl:variable name="failures" select="sum(//testsuite/@failures)" />
                <xsl:variable name="errors" select="sum(//testsuite/@errors)" />
                <xsl:variable name="skipped" select="sum(//testsuite/@skipped)" />
                <div class="mdc-chip-set" role="grid">
                    <div class="mdc-chip info" role="row">
                        <span class="mdc-chip__text">Total: <xsl:value-of select="$tests" />
                        </span>
                    </div>
                    <div class="mdc-chip success" role="row">
                        <span class="mdc-chip__text">Passed: <xsl:value-of
                                select="$tests - $failures - $errors - $skipped" />
                        </span>
                    </div>
                    <div class="mdc-chip error" role="row">
                        <span class="mdc-chip__text">Failed: <xsl:value-of select="$failures" />
                        </span>
                    </div>
                    <div class="mdc-chip warning" role="row">
                        <span class="mdc-chip__text">Errors: <xsl:value-of select="$errors" />
                        </span>
                    </div>
                    <div class="mdc-chip skip" role="row">
                        <span class="mdc-chip__text">Skipped: <xsl:value-of select="$skipped" />
                        </span>
                    </div>
                </div>
                <h2 class="mdc-typography--headline3">Test Suites</h2>
                <xsl:apply-templates select="testsuite" />
            </body>
        </html>
    </xsl:template>
    <xsl:template match="testsuite">
        <xsl:variable name="tests" select="@tests" />
        <xsl:variable name="failures"
            select="@failures" />
        <xsl:variable name="errors" select="@errors" />
        <xsl:variable name="skipped" select="@skipped" />
        <xsl:variable name="success"
            select="$tests - $failures - $errors - $skipped" />
        <div class="mdc-card"
            style="margin-bottom: 24px;">
            <div class="mdc-card__content">
                <h2 class="mdc-typography--headline6">
                    <xsl:value-of select="@name" />
                </h2>
                <div class="mdc-chip-set" role="grid">
                    <div class="mdc-chip info" role="row">
                        <span class="mdc-chip__text">Total: <xsl:value-of select="$tests" />
                        </span>
                    </div>
                    <div class="mdc-chip success" role="row">
                        <span class="mdc-chip__text">Passed: <xsl:value-of
                                select="$tests - $failures - $errors - $skipped" />
                        </span>
                    </div>
                    <div class="mdc-chip error" role="row">
                        <span class="mdc-chip__text">Failed: <xsl:value-of select="$failures" />
                        </span>
                    </div>
                    <div class="mdc-chip warning" role="row">
                        <span class="mdc-chip__text">Errors: <xsl:value-of select="$errors" />
                        </span>
                    </div>
                    <div class="mdc-chip skip" role="row">
                        <span class="mdc-chip__text">Skipped: <xsl:value-of select="$skipped" />
                        </span>
                    </div>
                </div>
            </div>
            <div class="mdc-card__actions">
                <button class="mdc-button mdc-card__action mdc-card__action--button" onclick="toggleDetails('suite-{generate-id()}')">
                    <div class="mdc-button__ripple"></div>
                    <span class="mdc-button__label">View Details</span>
                </button>
            </div>
        </div>
        <div id="suite-{generate-id()}" style="display: none;">
            <ul class="mdc-list mdc-list--two-line">
                <xsl:apply-templates select="testcase" />
            </ul>
        </div>
    </xsl:template>
    <xsl:template match="testcase">
        <xsl:param name="parent-type" />
        <xsl:param name="show-details" />
        <xsl:variable name="identity" select="concat('test-', $parent-type, '-', generate-id())" />
            <li class="mdc-list-item mdc-list-item--with-two-lines" tabindex="0">
            <span class="mdc-list-item__ripple"></span>
            <span class="mdc-list-item__start">
                <xsl:choose>
                    <xsl:when test="failure">
                        <i class="material-icons" style="color: var(--mdc-theme-error)">error</i>
                    </xsl:when>
                    <xsl:when test="error">
                        <i class="material-icons" style="color: var(--mdc-theme-error)">warning</i>
                    </xsl:when>
                    <xsl:otherwise>
                        <i class="material-icons" style="color: var(--mdc-theme-success)">
                            check_circle</i>
                    </xsl:otherwise>
                </xsl:choose>
            </span>
            <span class="mdc-list-item__content">
                <span class="mdc-list-item__primary-text">
                    <xsl:value-of select="@name" />
                </span>
                <span class="mdc-list-item__secondary-text">
                    <xsl:value-of select="@classname" />
                </span>
            </span>
            <span class="mdc-list-item__end">
                <button class="mdc-icon-button" aria-label="Expand details"
                    onclick="toggleDetails('test-{generate-id()}')">
                    <i class="material-icons">expand_more</i>
                </button>
            </span>
        </li>
            <li id="test-{generate-id()}" style="display: none;">
            <div class="mdc-card" style="margin: 16px;">
                <div class="mdc-card__content" style="padding: 16px;">
                    <button class="mdc-button mdc-button--raised" onclick="copyErrorLog('error-log-{generate-id()}')" data-target="error-log-{generate-id()}">
                        <span class="mdc-button__ripple"></span>
                        <i class="material-icons mdc-button__icon" aria-hidden="true">content_copy</i>
                        <span class="mdc-button__label">Copy</span>
                    </button>
                    <pre id="error-log-{generate-id()}" class="mdc-typography--body2" style="white-space: pre-wrap; word-break: break-word; margin: 0;">
                      <xsl:value-of select="failure"/>
                      <xsl:value-of select="error"/>
                      <xsl:value-of select="system-out"/>
                    </pre>
                </div>
            </div>
        </li>
    </xsl:template>
</xsl:stylesheet>