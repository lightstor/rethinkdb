// Autogenerated by metajava.py.
// Do not edit this file directly.
// The template for this file is located at:
// ../../../../../../../templates/Enum.java
package com.rethinkdb.proto;

public enum Protocol {

    PROTOBUF(656407617),
    JSON(2120839367);

    public final int value;

    private Protocol(int value){
        this.value = value;
    }

    public static Protocol fromValue(int value) {
        switch (value) {
            case 656407617: return Protocol.PROTOBUF;
            case 2120839367: return Protocol.JSON;
            default:
                throw new IllegalArgumentException(String.format(
                "%s is not a legal value for Protocol", value));
        }
    }
}
