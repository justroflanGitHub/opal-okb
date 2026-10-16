
void FUN_0000_2948(void)

{
  int in_BX;
  int iVar1;
  undefined1 *unaff_SI;
  char *unaff_DI;
  undefined2 unaff_ES;
  undefined2 unaff_DS;
  
code_r0x00002948:
  iVar1 = in_BX + -1;
  do {
    iVar1 = iVar1 + 1;
  } while (unaff_DI[iVar1] == ' ');
  if (unaff_DI[iVar1] == '=') {
    do {
      iVar1 = iVar1 + 1;
    } while (unaff_DI[iVar1] == ' ');
    FUN_0100_1722(unaff_DI + iVar1);
  }
  else {
    while( true ) {
      in_BX = -1;
      if ((*unaff_DI == '\0') && (unaff_DI[1] == '\0')) break;
      do {
        in_BX = in_BX + 1;
        if (unaff_SI[in_BX] == '\n') goto code_r0x00002948;
      } while (unaff_DI[in_BX] == unaff_SI[in_BX]);
      unaff_DI = unaff_DI + 1;
    }
    *unaff_SI = 0;
  }
  return;
}

