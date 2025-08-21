$body = @'
{"symbols":["000001"],"period":"1y"}
'@

try {
    $response = Invoke-RestMethod -Method Post -Uri http://localhost:8000/api/analyze -ContentType 'application/json' -Body $body
    Write-Output "API调用成功！"
    $response | ConvertTo-Json -Depth 6
} catch {
    Write-Error "API调用失败: $($_.Exception.Message)"
    if ($_.Exception.Response) {
        $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
        $responseBody = $reader.ReadToEnd()
        Write-Output "响应内容: $responseBody"
    }
}