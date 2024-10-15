// bracket-functions.js
function saveFn(data, userData) {
    var json = jQuery.toJSON(data)
    $('#saveOutput').text(JSON.stringify(data, null, 2))
}

function edit_fn(container, data, place, time, doneCb) {
    var input = $('<input type="text">')
    input.val(data ? data.flag + ':' + data.name : '')
    container.html(input)
    input.focus()
    input.blur(function () {
        var inputValue = input.val()
        if (inputValue.length === 0) {
            doneCb(null); // Drop the team and replace with BYE
        } else {
            var flagAndName = inputValue.split(':') // Expects correct input
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
            container.append(data.name)
            return;
    }
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

function transformData(originalData) {
    let teams = [];
    let results = [];
    let driver_pair_order = driver_order_setting(originalData.Timedata)
    let exit_loop = false
    let skip_entry = false
    let finale = []
    let semi_finale = []

    var heat_count = Math.ceil(Math.log2(originalData.Timedata["1"].length));

    // Check if the required data exists and is in the correct format
    if (originalData && originalData.Timedata && Array.isArray(originalData.Timedata["1"])) {
        for (let i = 0; i < originalData.Timedata["1"].length; i += 2) {

            if (i + 1 < originalData.Timedata["1"].length) {
                // Create a pair with the current and next team
                let pair = [
                    { "name": originalData.Timedata["1"][i][1] + " " + originalData.Timedata["1"][i][2], "flag": "no" },
                    { "name": originalData.Timedata["1"][i + 1][1] + " " + originalData.Timedata["1"][i + 1][2], "flag": "no" }
                ];
                teams.push(pair);
            } else {
                // If there's no pair (odd number of teams), add the last team alone
                let single = { "name": originalData.Timedata["1"][i][1], "flag": "no" };
                teams.push([single]);
            }
        }
    } else {
        console.error('Data is not available or in an unexpected format');
    }
    const isEven = num => num % 2 === 0;
    full_loc_array = []
    count = 0
    console.log(driver_pair_order)



    for (let key in originalData.Timedata) {
        med_loc_array = []
        if (originalData.Timedata.hasOwnProperty(key)) {
            
            let dataArray = originalData.Timedata[key];
            console.log(key)
            if (key == 1) { 
              num = key
            } else {
              num = (key - 1)
            }

            for (let driver_o in driver_pair_order[num]) {
              
              for (let i = 0; i < dataArray.length; i += 1) {


                    if (typeof new_loc_array == 'undefined') {
                          new_loc_array = []
                        }
                    console.log(heat_count, key)
                    
                    if (heat_count == key) {
                      let finale_pair = []
                      let semi_finale_pair = []

                      let tmp_finale_pair = []
                      let tmp_semi_finale = []


                      count += 1
                      console.log(driver_pair_order[(key -1)])
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
                      console.log(tmp_finale_pair, "finale")
                      console.log(tmp_semi_finale, "semi")
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

                        if (dataArray[i][6] == 1) {
                          entry = 11111111
                        } else if (dataArray[i][6] == 2) {
                          entry = 22222222

                        } else if (dataArray[i][6] == 3)
                          entry = 33333333

                        else {
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
          if (exit_loop == true) {break}
      }
        }
        full_loc_array.push(med_loc_array)
    }
    results = full_loc_array
    data = {teams, results}
    return data

}

function initializeBracket(race_title, date) {
    var url = "/get_stige_data";
    var event = {'date': date, "race_title": race_title};

    $.ajax({
        url: url,
        type: 'POST',
        data: JSON.stringify(event),
        contentType: 'application/json',
        dataType: 'json',
        success: function(data) {
            var new_data = transformData(data);

            var drivers_num = new_data.teams.length * 2;
            var teamWidth, scoreWidth, matchMargin, roundMargin;

            if (window.innerWidth <= 768) {
                teamWidth = 150;
                scoreWidth = 30;
                matchMargin = 25;
                roundMargin = 40;
            } else {
                teamWidth = 200;
                scoreWidth = 40;
                matchMargin = 40;
                roundMargin = 60;
                if (drivers_num <= 8) {
                    matchMargin = 50;
                    roundMargin = 80;
                } else if (drivers_num <= 4) {
                    matchMargin = 60;
                    roundMargin = 100;
                }
            }

            $('#doubleElimination').bracket({
                dir: 'lr',
                teamWidth: teamWidth,
                scoreWidth: scoreWidth,
                matchMargin: matchMargin,
                roundMargin: roundMargin,
                centerConnectors: true,
                init: new_data,
                decorator: {
                    edit: edit_fn,
                    render: render_fn
                }
            });

            // Force reflow to ensure proper layout
            $('#doubleElimination').hide().show(0);

            // Adjust scroll position to show the start of the bracket
            document.querySelector('.turnament-bracket').scrollLeft = 0;
        },
        error: function(jqXHR, textStatus, errorThrown) {
            console.error("Error: " + textStatus, errorThrown);
        }
    });
}