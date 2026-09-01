(async function() {
    const c = {
        reset: "\x1b[0m",
        bright: "\x1b[1m",
        dim: "\x1b[2m",
        red: "\x1b[31m",
        green: "\x1b[32m",
        yellow: "\x1b[33m",
        blue: "\x1b[34m",
        magenta: "\x1b[35m",
        cyan: "\x1b[36m",
        white: "\x1b[37m",
        bgRed: "\x1b[41m",
        bgGreen: "\x1b[42m",
        bgYellow: "\x1b[43m",
        bgBlue: "\x1b[44m"
    };
    
    const log = {
        info: (msg) => console.log(c.blue + "[INF]" + c.reset + " " + msg),
        success: (msg) => console.log(c.green + "[OK]" + c.reset + " " + msg),
        warn: (msg) => console.log(c.yellow + "[!]" + c.reset + " " + msg),
        error: (msg) => console.log(c.red + "[ERR]" + c.reset + " " + msg),
        rate: (msg) => console.log(c.magenta + "[RATE]" + c.reset + " " + msg),
        del: (msg) => console.log(c.cyan + "[DEL]" + c.reset + " " + msg),
        skip: (msg) => console.log(c.dim + "[SKIP]" + c.reset + " " + msg),
        batch: (msg) => console.log(c.yellow + "[BATCH]" + c.reset + " " + msg),
        stop: (msg) => console.log(c.red + "[STOP]" + c.reset + " " + msg),
        done: (msg) => console.log(c.green + c.bright + "[DONE]" + c.reset + " " + msg),
        progress: (msg) => console.log(c.cyan + c.bright + "[PRG]" + c.reset + " " + msg),
        prompt: (msg) => console.log(c.magenta + c.bright + "[?]" + c.reset + " " + msg)
    };
    
    const wait = async (ms) => {
        if (ms > 60000) {
            log.warn("Long wait detected: " + (ms/60000).toFixed(1) + " minutes");
        }
        await new Promise(r => setTimeout(r, ms));
    };
    
    const getInput = (prompt) => {
        return new Promise((resolve) => {
            const readline = require('readline');
            const rl = readline.createInterface({
                input: process.stdin,
                output: process.stdout
            });
            rl.question(prompt, (answer) => {
                rl.close();
                resolve(answer.trim());
            });
        });
    };
    
    log.prompt("========================================");
    log.prompt("DISCORD CLEANER | by @tc4dy <3");
    log.prompt("========================================");
    log.info("This script will delete all messages from a specific user in a channel");
    log.warn("This action cannot be undone!");
    log.info("========================================");
    
    let authToken = "ENTER YOUR TOKEN BROS";
    let authorId = "ENTER YOUR ID";
    let channelId = "ENTER THE CHANEL ID <3";
    
    while (!authToken || authToken.length < 10) {
        authToken = await getInput(c.magenta + "[?] Enter your Discord token: " + c.reset);
        if (!authToken || authToken.length < 10) {
            log.error("Invalid token! Token must be at least 10 characters.");
        }
    }
    
    while (!authorId || authorId.length < 10) {
        authorId = await getInput(c.magenta + "[?] Enter the user ID to delete messages from: " + c.reset);
        if (!authorId || authorId.length < 10) {
            log.error("Invalid user ID! ID must be at least 10 digits.");
        }
    }
    
    while (!channelId || channelId.length < 10) {
        channelId = await getInput(c.magenta + "[?] Enter the channel ID: " + c.reset);
        if (!channelId || channelId.length < 10) {
            log.error("Invalid channel ID! ID must be at least 10 digits.");
        }
    }
    
    log.success("All inputs validated!");
    log.info("Target user: " + authorId);
    log.info("Target channel: " + channelId);
    log.warn("Starting deletion process...");
    
    let shouldStop = false;
    window.stopDeleting = function() {
        shouldStop = true;
        log.stop("Stopping gracefully...");
    };
    log.info("Type 'stopDeleting()' to stop the script");
    
    let deleted = 0;
    let failed = 0;
    let skipped = 0;
    let totalChecked = 0;
    let beforeMessageId = null;
    let deleteDelay = 1000;
    let searchDelay = 2000;
    let consecutiveRateLimits = 0;
    let deletedIds = new Set();
    let totalRateLimitWaits = 0;
    let startTime = Date.now();
    let lastBatchTime = Date.now();
    let totalApiCalls = 0;
    let totalErrors = 0;
    let maxRetries = 10;
    let isPaused = false;
    let lastSuccessTime = Date.now();
    let consecutiveFailures = 0;
    let maxConsecutiveFailures = 20;
    
    const getStats = () => {
        const elapsed = (Date.now() - startTime) / 1000;
        const speed = deleted > 0 ? (deleted / elapsed).toFixed(2) : 0;
        return {
            elapsed: elapsed,
            speed: speed,
            deleted: deleted,
            failed: failed,
            skipped: skipped,
            total: totalChecked,
            rateLimits: totalRateLimitWaits,
            errors: totalErrors
        };
    };
    
    const printStats = () => {
        const s = getStats();
        const hours = Math.floor(s.elapsed / 3600);
        const minutes = Math.floor((s.elapsed % 3600) / 60);
        const seconds = Math.floor(s.elapsed % 60);
        const timeStr = hours > 0 ? hours + "h " + minutes + "m " + seconds + "s" : minutes > 0 ? minutes + "m " + seconds + "s" : seconds + "s";
        log.progress("[+] " + s.deleted + " deleted | [-] " + s.failed + " failed | [*] " + s.skipped + " skipped | [R] " + s.rateLimits + " rate limits | [S] " + s.speed + " msg/s | [T] " + timeStr);
    };
    
    const handleRateLimit = async (resp, isDelete = false) => {
        const data = await resp.json();
        let waitTime = data.retry_after * 1000;
        if (waitTime < 10000) waitTime = 10000;
        waitTime = waitTime + (isDelete ? 5000 : 10000);
        consecutiveRateLimits++;
        totalRateLimitWaits++;
        log.rate("Rate limited! Waiting " + (waitTime/1000).toFixed(1) + " seconds... (Total: " + totalRateLimitWaits + ")");
        if (consecutiveRateLimits > 5) {
            deleteDelay = Math.min(deleteDelay + 1000, 10000);
            searchDelay = Math.min(searchDelay + 1000, 10000);
            log.rate("Increased delays to " + deleteDelay + "ms (delete) and " + searchDelay + "ms (search)");
        }
        await wait(waitTime);
        if (consecutiveRateLimits > 10) {
            log.warn("Too many rate limits, pausing for 60 seconds...");
            await wait(60000);
            consecutiveRateLimits = 0;
        }
        return true;
    };
    
    const safeFetch = async (url, options, retryCount = 0) => {
        try {
            totalApiCalls++;
            const resp = await fetch(url, options);
            if (resp.status === 429) {
                await handleRateLimit(resp, options.method === "DELETE");
                return await safeFetch(url, options, retryCount + 1);
            }
            if (resp.status === 401) {
                log.error("Authentication failed! Token is invalid or expired.");
                shouldStop = true;
                return null;
            }
            if (resp.status === 403) {
                log.error("Access forbidden! You don't have permission.");
                shouldStop = true;
                return null;
            }
            if (resp.status === 404) {
                return resp;
            }
            if (!resp.ok && retryCount < maxRetries) {
                log.warn("Request failed (" + resp.status + "), retrying " + (retryCount + 1) + "/" + maxRetries);
                await wait(2000 * (retryCount + 1));
                return await safeFetch(url, options, retryCount + 1);
            }
            if (!resp.ok) {
                log.error("Request failed permanently: " + resp.status + " " + resp.statusText);
                totalErrors++;
                return resp;
            }
            consecutiveFailures = 0;
            lastSuccessTime = Date.now();
            return resp;
        } catch (err) {
            totalErrors++;
            consecutiveFailures++;
            log.error("Network error: " + err.message);
            if (consecutiveFailures > maxConsecutiveFailures) {
                log.error("Too many consecutive failures, pausing for 30 seconds...");
                await wait(30000);
                consecutiveFailures = 0;
            }
            if (retryCount < maxRetries) {
                log.warn("Retrying " + (retryCount + 1) + "/" + maxRetries);
                await wait(5000 * (retryCount + 1));
                return await safeFetch(url, options, retryCount + 1);
            }
            return null;
        }
    };
    
    while (!shouldStop) {
        try {
            if (isPaused) {
                await wait(1000);
                continue;
            }
            
            let url = "https://discord.com/api/v9/channels/" + channelId + "/messages?limit=100";
            if (beforeMessageId) {
                url += "&before=" + beforeMessageId;
            }
            
            const resp = await safeFetch(url, {
                headers: {
                    "Authorization": authToken,
                    "Content-Type": "application/json"
                }
            });
            
            if (!resp) {
                if (shouldStop) break;
                log.error("Failed to fetch messages, waiting 10 seconds...");
                await wait(10000);
                continue;
            }
            
            if (resp.status === 429) {
                continue;
            }
            
            if (!resp.ok) {
                log.error("API error: " + resp.status + " " + resp.statusText);
                if (resp.status === 401 || resp.status === 403) {
                    break;
                }
                await wait(10000);
                continue;
            }
            
            const messages = await resp.json();
            
            if (!messages || messages.length === 0) {
                log.done("All messages scanned!");
                break;
            }
            
            const myMessages = messages.filter(m => m.author.id === authorId && !deletedIds.has(m.id));
            totalChecked += messages.length;
            
            log.info("Checked " + messages.length + " messages, found " + myMessages.length + " to delete (Total checked: " + totalChecked + ")");
            
            if (myMessages.length === 0) {
                if (messages.length > 0) {
                    beforeMessageId = messages[messages.length - 1].id;
                    log.skip("No messages to delete in this batch, continuing...");
                }
                await wait(1000);
                continue;
            }
            
            let batchSize = 3;
            let deletedInBatch = 0;
            let failedInBatch = 0;
            
            for (let i = 0; i < myMessages.length; i += batchSize) {
                if (shouldStop) {
                    log.stop("Stopped after deleting " + deleted + " messages!");
                    break;
                }
                
                if (isPaused) {
                    await wait(1000);
                    continue;
                }
                
                const batch = myMessages.slice(i, i + batchSize);
                log.batch("Processing " + batch.length + " messages (Batch " + (Math.floor(i/batchSize) + 1) + "/" + Math.ceil(myMessages.length/batchSize) + ")");
                
                for (const msg of batch) {
                    if (shouldStop) break;
                    if (isPaused) {
                        await wait(1000);
                        continue;
                    }
                    
                    if (deletedIds.has(msg.id)) {
                        log.skip("Message already deleted: " + msg.id);
                        skipped++;
                        continue;
                    }
                    
                    try {
                        const delResp = await safeFetch(
                            "https://discord.com/api/v9/channels/" + channelId + "/messages/" + msg.id,
                            {
                                headers: { "Authorization": authToken },
                                method: "DELETE"
                            }
                        );
                        
                        if (!delResp) {
                            failed++;
                            failedInBatch++;
                            log.error("Failed to delete message: " + msg.id);
                            continue;
                        }
                        
                        if (delResp.status === 429) {
                            i -= batchSize;
                            break;
                        }
                        
                        if (delResp.ok) {
                            deleted++;
                            deletedInBatch++;
                            deletedIds.add(msg.id);
                            const content = msg.content ? msg.content.slice(0, 30) : "[empty/attachment]";
                            log.del("[" + deleted + "] Deleted: " + content + (msg.content && msg.content.length > 30 ? "..." : ""));
                            lastSuccessTime = Date.now();
                        } else if (delResp.status === 404) {
                            log.skip("Message already deleted: " + msg.id);
                            skipped++;
                            deletedIds.add(msg.id);
                        } else if (delResp.status === 429) {
                            i -= batchSize;
                            break;
                        } else {
                            failed++;
                            failedInBatch++;
                            log.error("Failed to delete: " + msg.id + " (" + delResp.status + ")");
                        }
                        
                        const now = Date.now();
                        if (now - lastSuccessTime > 30000) {
                            log.warn("No successful deletions in 30 seconds, checking connection...");
                            await wait(1000);
                        }
                        
                        await wait(deleteDelay);
                        
                    } catch (err) {
                        failed++;
                        failedInBatch++;
                        totalErrors++;
                        log.error("Error deleting message: " + err.message);
                        await wait(5000);
                    }
                }
                
                if (deletedInBatch > 5) {
                    log.warn("Deleting too fast, slowing down...");
                    await wait(5000);
                }
                
                if (failedInBatch > batchSize) {
                    log.error("Too many failures in batch, pausing...");
                    await wait(10000);
                    failedInBatch = 0;
                }
                
                if (totalErrors > 50) {
                    log.error("Too many errors (" + totalErrors + "), pausing for 30 seconds...");
                    await wait(30000);
                    totalErrors = 0;
                }
                
                deletedInBatch = 0;
                failedInBatch = 0;
                
                if (deleted % 10 === 0 && deleted > 0) {
                    printStats();
                }
            }
            
            if (messages.length > 0) {
                beforeMessageId = messages[messages.length - 1].id;
                log.info("Loading next batch in " + (searchDelay/1000) + " seconds...");
                await wait(searchDelay);
            }
            
            if (Date.now() - lastBatchTime > 60000) {
                log.warn("Last batch took more than 60 seconds, checking health...");
                if (consecutiveRateLimits > 3) {
                    log.warn("High rate limit count, reducing speed...");
                    deleteDelay = Math.min(deleteDelay + 500, 10000);
                    searchDelay = Math.min(searchDelay + 500, 10000);
                }
                lastBatchTime = Date.now();
            }
            
        } catch (err) {
            totalErrors++;
            log.error("Critical error: " + err.message);
            log.warn("Restarting loop in 10 seconds...");
            await wait(10000);
            if (totalErrors > 100) {
                log.error("Too many errors (" + totalErrors + "), forcing pause for 60 seconds...");
                await wait(60000);
                totalErrors = 0;
            }
            continue;
        }
    }
    
    const elapsed = (Date.now() - startTime) / 1000;
    const hours = Math.floor(elapsed / 3600);
    const minutes = Math.floor((elapsed % 3600) / 60);
    const seconds = Math.floor(elapsed % 60);
    const timeStr = hours > 0 ? hours + "h " + minutes + "m " + seconds + "s" : minutes > 0 ? minutes + "m " + seconds + "s" : seconds + "s";
    
    log.done("========================================");
    log.done("PROCESS COMPLETED");
    log.done("========================================");
    log.success("[+] Deleted: " + deleted + " messages");
    log.error("[-] Failed: " + failed + " messages");
    log.info("[*] Skipped: " + skipped + " messages");
    log.info("[C] Total checked: " + totalChecked + " messages");
    log.info("[R] Rate limits: " + totalRateLimitWaits + " times");
    log.info("[E] Total errors: " + totalErrors);
    log.info("[A] API calls: " + totalApiCalls);
    log.info("[T] Time elapsed: " + timeStr);
    if (deleted > 0) {
        log.success("[S] Average speed: " + (deleted / elapsed).toFixed(2) + " messages/second");
    }
    log.done("========================================");
    log.info("Finished at: " + new Date().toLocaleString());
})();
