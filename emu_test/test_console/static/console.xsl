<?xml version="1.0" encoding="UTF-8"?>
<html xsl:version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
<head>
  <link rel="stylesheet" type="text/css" href="console.css"></link>
</head>
<body class="interface">
  <h1><a href="http://go/emu_console_test">Emulator Conolse Test</a></h1>
  <div class="info">
    <h2>Test Name: <xsl:for-each select="result/testMethodName"><xsl:value-of select="@name"/></xsl:for-each></h2>
    <h2>AVD Config: <xsl:for-each select="result/avdConfigName"><xsl:value-of select="@name"/></xsl:for-each></h2>
    <div class="resultSummary">
    <h2>Result Summary</h2>
    <table class="summary">
      <tr>
        <th class="summary">Total</th>
        <th class="summary">Passes</th>
        <th class="summary">Failures</th>
        <th class="summary">Errors</th>
        <th class="summary">ExpectedFailures</th>
        <th class="summary">UnexpectedSuccesses</th>
      </tr>
      <tr>
        <td class="DevStatus"><xsl:for-each select="result/resultSummary/total"><xsl:value-of select="@num"/></xsl:for-each></td>
        <td class="DevStatus Pass"><xsl:for-each select="result/resultSummary/passes"><xsl:value-of select="@num"/></xsl:for-each></td>
        <td class="DevStatus Failure"><xsl:for-each select="result/resultSummary/failures"><xsl:value-of select="@num"/></xsl:for-each></td>
        <td class="DevStatus Error"><xsl:for-each select="result/resultSummary/errors"><xsl:value-of select="@num"/></xsl:for-each></td>
        <td class="DevStatus"><xsl:for-each select="result/resultSummary/expectedFailures"><xsl:value-of select="@num"/></xsl:for-each></td>
        <td class="DevStatus"><xsl:for-each select="result/resultSummary/unexpectedSuccesses"><xsl:value-of select="@num"/></xsl:for-each></td>
      </tr>
    </table>
    </div>
  </div>
  <table>
    <tr>
      <th>Unittest Name</th>
      <th>Result</th>
    </tr>

    <xsl:for-each select="result/Passes/test">
      <tr>
        <td class="DevName"><xsl:value-of select="@name"/></td>
        <td class="DevStatus Pass"><xsl:value-of select="@test_result"/></td>
      </tr>
    </xsl:for-each>

    <xsl:for-each select="result/Failures/test">
      <tr>
        <td class="DevName"><xsl:value-of select="@name"/></td>
        <td class="DevStatus Failure"><xsl:value-of select="@test_result"/></td>
      </tr>
    </xsl:for-each>

    <xsl:for-each select="result/Errors/test">
      <tr>
        <td class="DevName"><xsl:value-of select="@name"/></td>
        <td class="DevStatus Error"><xsl:value-of select="@test_result"/></td>
      </tr>
    </xsl:for-each>

    <xsl:for-each select="result/ExpectedFailures/test">
      <tr>
        <td class="DevName"><xsl:value-of select="@name"/></td>
        <td class="DevStatus"><xsl:value-of select="@test_result"/></td>
      </tr>
    </xsl:for-each>

    <xsl:for-each select="result/UnexpectedSuccesses/test">
      <tr>
        <td class="DevName"><xsl:value-of select="@name"/></td>
        <td class="DevStatus"><xsl:value-of select="@test_result"/></td>
      </tr>
    </xsl:for-each>
  </table>
</body>
</html>
