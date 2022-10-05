<?xml version="1.0" encoding="UTF-8" ?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
<xsl:output method="xml" omit-xml-declaration="yes" />
<xsl:template match="testsuite">
Test Results For <xsl:value-of select="@name"/>
TOTAL=<xsl:value-of select="@tests"/>, PASSED=<xsl:value-of select="@tests - @failures - @errors - @skipped"/>, FAILED=<xsl:value-of select="@failures"/>, ERRORS=<xsl:value-of select="@errors"/>, SKIPPED=<xsl:value-of select="@skipped"/>

Showing first failure:
<xsl:apply-templates select="(//failure)[1]"/>
</xsl:template>
<xsl:template match="//failure">
================== <xsl:value-of select="../@classname"/><xsl:value-of select="../@name"/> =============
<xsl:value-of select="@message"/>
--
<xsl:value-of select="../system-out"/>
</xsl:template>
</xsl:stylesheet>