
function initializeBracket(data, eventIndex) {
    console.log(`Initializing bracket for event ${eventIndex}`);
    console.log('Bracket data:', data);

    const driversNum = data.teams.length * 2;

    let teamWidth, scoreWidth, matchMargin, roundMargin;
    if (driversNum <= 4) {
        teamWidth = 300;
        scoreWidth = 60;
        matchMargin = 100;
        roundMargin = 100;
    } else if (driversNum <= 8) {
        teamWidth = 300;
        scoreWidth = 60;
        matchMargin = 100;
        roundMargin = 100;
    } else if (driversNum <= 16) {
        teamWidth = 220;
        scoreWidth = 60;
        matchMargin = 30;
        roundMargin = 80;
    } else {
        teamWidth = 250;
        scoreWidth = 60;
        matchMargin = 15;
        roundMargin = 80;
    }

    console.log(`Bracket settings for event ${eventIndex}:`, { teamWidth, scoreWidth, matchMargin, roundMargin });

    const bracketElement = $(`#doubleElimination${eventIndex}`);
    console.log(`Bracket element for event ${eventIndex}:`, bracketElement);

    if (bracketElement.length === 0) {
        console.error(`Bracket element not found for event ${eventIndex}`);
        return;
    }

    try {
        bracketElement.bracket({
            init: data,
            save: saveFn,  // We'll define this function
            decorator: {
                edit: edit_fn,
                render: render_fn
            },
            dir: 'lr',
            teamWidth: teamWidth,
            scoreWidth: scoreWidth,
            matchMargin: matchMargin,
            roundMargin: roundMargin,
            centerConnectors: true
        });
        console.log(`Bracket initialization complete for event ${eventIndex}`);
    } catch (error) {
        console.error(`Error initializing bracket for event ${eventIndex}:`, error);
    }
}

// Define the saveFn function
function saveFn(data, userData) {
    console.log('Bracket data saved:', data);
    // Implement saving logic here if needed
}

function transformData(originalData) {
    let teams = [];
    let results = [];
    let driver_pair_order = driver_order_setting(originalData.Timedata)
    let exit_loop = false
    let finale = []
    let semi_finale = []

    var heat_count = Math.ceil(Math.log2(originalData.Timedata["1"].length));
    if (originalData && originalData.Timedata && Array.isArray(originalData.Timedata["1"])) {
        for (let i = 0; i < originalData.Timedata["1"].length; i += 2) {
            if (i + 1 < originalData.Timedata["1"].length) {
                let pair = [
                    { "name": originalData.Timedata["1"][i][1] + " " + originalData.Timedata["1"][i][2], "flag": "no" },
                    { "name": originalData.Timedata["1"][i + 1][1] + " " + originalData.Timedata["1"][i + 1][2], "flag": "no" }
                ];

                teams.push(pair);
                console.log()
            } else {
                let single = { "name": originalData.Timedata["1"][i][1], "flag": "no" };
                teams.push([single]);
            }
        }
    } else {
        console.error('Data is not available or in an unexpected format');
    }

    let full_loc_array = []
    let count = 0

    for (let key in originalData.Timedata) {
        let med_loc_array = []
        if (originalData.Timedata.hasOwnProperty(key)) {
            let dataArray = originalData.Timedata[key];
            let num = key == 1 ? key : key - 1;

            for (let driver_o in driver_pair_order[num]) {
                for (let i = 0; i < dataArray.length; i += 1) {
                    let new_loc_array = []
                    
                    if (heat_count == key) {
                        let finale_pair = []
                        let semi_finale_pair = []
                        let tmp_finale_pair = []
                        let tmp_semi_finale = []

                        count += 1
                        let tmp_key = (key -1)
                        if (driver_pair_order[(tmp_key)][0][7] > driver_pair_order[(tmp_key)][1][7] && driver_pair_order[(tmp_key)][1][6] == 0) {
                            tmp_semi_finale.push(driver_pair_order[(tmp_key)][0])
                            tmp_finale_pair.push(driver_pair_order[(tmp_key)][1])
                        } else {
                            tmp_semi_finale.push(driver_pair_order[(tmp_key)][1])
                            tmp_finale_pair.push(driver_pair_order[(tmp_key)][0])
                        }

                        if (driver_pair_order[(tmp_key)][2][7] > driver_pair_order[(tmp_key)][3][7] && driver_pair_order[(tmp_key)][3][6] == 0) {
                            tmp_semi_finale.push(driver_pair_order[(tmp_key)][2])
                            tmp_finale_pair.push(driver_pair_order[(tmp_key)][3])
                        } else {
                            tmp_semi_finale.push(driver_pair_order[(tmp_key)][3])
                            tmp_finale_pair.push(driver_pair_order[(tmp_key)][2])
                        }

                        for (let b in driver_pair_order[(tmp_key)]) {
                            for (let g in tmp_finale_pair) {
                                if (tmp_finale_pair[g][7] == driver_pair_order[(tmp_key)][b][7]) {
                                    for (let h in driver_pair_order[(key)]) {
                                        if (driver_pair_order[key][h][0] == tmp_finale_pair[g][0]) {
                                            if (driver_pair_order[key][h][6] == 1) {
                                                finale_pair.push(11111111)
                                            } else if (driver_pair_order[key][h][6] == 2) {
                                                finale_pair.push(22222222)
                                            } else if (driver_pair_order[key][h][6] == 3) {
                                                finale_pair.push(33333333)
                                            } else {
                                                finale_pair.push(driver_pair_order[key][h][7])
                                            }
                                        }
                                    }
                                }
                            }

                            for (let g in tmp_semi_finale) {
                                if (tmp_semi_finale[g][7] == driver_pair_order[(tmp_key)][b][7]) {
                                    for (let h in driver_pair_order[(key)]) {
                                        if (driver_pair_order[key][h][0] == tmp_semi_finale[g][0]) {
                                            if (driver_pair_order[key][h][6] == 1) {
                                                semi_finale_pair.push(11111111)
                                            } else if (driver_pair_order[key][h][6] == 2) {
                                                semi_finale_pair.push(22222222)
                                            } else if (driver_pair_order[key][h][6] == 3) {
                                                semi_finale_pair.push(33333333)
                                            } else {
                                                semi_finale_pair.push(driver_pair_order[key][h][7])
                                            }
                                        }
                                    }
                                }
                            }
                        }

                        med_loc_array.push(finale_pair)
                        med_loc_array.push(semi_finale_pair)
                        
                        exit_loop = true;
                        break
                    } else if (driver_pair_order[num][driver_o][0] == dataArray[i][0] && heat_count != key) {
                        count += 1

                        let entry;
                        if (dataArray[i][6] == 1) {
                            entry = 11111111
                        } else if (dataArray[i][6] == 2) {
                            entry = 22222222
                        } else if (dataArray[i][6] == 3) {
                            entry = 33333333
                        } else {
                            entry = dataArray[i][7]
                        }
                        new_loc_array.push(entry)

                        if (count == 2) {
                            count = 0
                            med_loc_array.push(new_loc_array)
                            new_loc_array = []
                            break;
                        }
                    } 
                }
                if (exit_loop) break;
            }
        }
        full_loc_array.push(med_loc_array)
    }
    results = full_loc_array
    return {teams, results}
}

function driver_order_setting(timedata) {
    var driver_order_object = {};
    for (const key in timedata) {
        if (timedata.hasOwnProperty(key)) {
            const dataArray = timedata[key];
            dataArray.forEach(entry => {
                if (!driver_order_object.hasOwnProperty(key)) {
                    driver_order_object[key] = [];
                }
                driver_order_object[key].push(entry);
            });
        }
    }
    return driver_order_object;
}

function edit_fn(container, data, doneCb) {
    var input = $('<input type="text">')
    input.val(data ? data.flag + ':' + data.name : '')
    container.html(input)
    input.focus()
    input.blur(function () {
        var inputValue = input.val()
        if (inputValue.length === 0) {
            doneCb(null);
        } else {
            var flagAndName = inputValue.split(':')
            doneCb({flag: flagAndName[0], name: flagAndName[1]})
        }
    })
}

function render_fn(container, data, score, state) {
    switch (state) {
        case "empty-bye":
            container.append("No team")
            return;
        case "empty-tbd":
            container.append("Upcoming")
            return;
        case "entry-no-score":
        case "entry-default-win":
        case "entry-complete":
            container.append(data.name).append();
            return;
    }
}